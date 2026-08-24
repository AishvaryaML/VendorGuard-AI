import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from app.main import app
from app.core.database import AsyncSessionLocal, init_db_connection
from app.models.vendor import Vendor, RiskTier, VendorStatus, MonitoringFrequency
from app.models.alert import Alert
from app.services.crawler import VendorCrawlerService


@pytest.mark.asyncio
async def test_monitoring_api_trigger_and_status():
    await init_db_connection()

    unique_domain = f"mon-api-{uuid.uuid4().hex[:8]}.com"
    target_url = f"https://{unique_domain}"

    async with AsyncSessionLocal() as session:
        vendor = Vendor(
            name="Monitoring API Vendor",
            domain=unique_domain,
            website_url=target_url,
            monitoring_frequency=MonitoringFrequency.DAILY,
            status=VendorStatus.ACTIVE
        )
        session.add(vendor)
        await session.commit()
        await session.refresh(vendor)
        vendor_id = vendor.id

    mock_crawl_data = {
        "vendor_domain": unique_domain,
        "normalized_start_url": target_url,
        "documents": []
    }

    with patch.object(VendorCrawlerService, "crawl_vendor", new=AsyncMock(return_value=mock_crawl_data)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Trigger POST /api/v1/monitoring/trigger
            res = await ac.post(f"/api/v1/monitoring/trigger?vendor_id={vendor_id}&force=true")
            assert res.status_code == 200, f"Error: {res.text}"
            data = res.json()
            assert data["monitored_count"] == 1
            assert data["results"][0]["vendor_id"] == vendor_id
            assert data["results"][0]["status"] == "Success"

            # 2. Get GET /api/v1/monitoring/status/{vendor_id}
            status_res = await ac.get(f"/api/v1/monitoring/status/{vendor_id}")
            assert status_res.status_code == 200
            st_data = status_res.json()
            assert st_data["vendor_id"] == vendor_id
            assert st_data["vendor_name"] == "Monitoring API Vendor"
            assert st_data["monitoring_frequency"] == "Daily"
            assert st_data["last_monitored_at"] is not None


@pytest.mark.asyncio
async def test_alerts_api_list_filtering_and_read():
    await init_db_connection()

    unique_domain = f"alert-api-{uuid.uuid4().hex[:8]}.com"

    async with AsyncSessionLocal() as session:
        vendor = Vendor(
            name="Alert API Vendor",
            domain=unique_domain,
            website_url=f"https://{unique_domain}",
            monitoring_frequency=MonitoringFrequency.DAILY
        )
        session.add(vendor)
        await session.commit()
        await session.refresh(vendor)
        vendor_id = vendor.id

        # Insert 3 Alerts (2 Policy Change, 1 Risk Degradation)
        a1 = Alert(
            vendor_id=vendor_id,
            alert_type="Policy Change",
            severity="Low",
            title="Policy Updated: Privacy Policy",
            description="Text changed in Privacy Policy.",
            is_read=False
        )
        a2 = Alert(
            vendor_id=vendor_id,
            alert_type="Policy Change",
            severity="Medium",
            title="Policy Updated: Terms of Service",
            description="Text changed in Terms of Service.",
            is_read=True
        )
        a3 = Alert(
            vendor_id=vendor_id,
            alert_type="Risk Degradation",
            severity="Critical",
            title="Risk Degradation Detected: Alert API Vendor",
            description="Risk score jumped by +35 points.",
            is_read=False
        )
        session.add_all([a1, a2, a3])
        await session.commit()
        await session.refresh(a1)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. GET /api/v1/alerts filtered by vendor_id
        res = await ac.get(f"/api/v1/alerts?vendor_id={vendor_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

        # 2. Filter by alert_type="Risk Degradation"
        res_deg = await ac.get(f"/api/v1/alerts?vendor_id={vendor_id}&alert_type=Risk%20Degradation")
        assert res_deg.status_code == 200
        deg_data = res_deg.json()
        assert deg_data["total"] == 1
        assert deg_data["items"][0]["severity"] == "Critical"

        # 3. Filter by is_read=false
        res_unread = await ac.get(f"/api/v1/alerts?vendor_id={vendor_id}&is_read=false")
        assert res_unread.status_code == 200
        unread_data = res_unread.json()
        assert unread_data["total"] == 2

        # 4. PATCH /api/v1/alerts/{id}/read
        read_res = await ac.patch(f"/api/v1/alerts/{a1.id}/read")
        assert read_res.status_code == 200
        assert read_res.json()["is_read"] is True

        # Verify unread count is now 1
        res_unread_after = await ac.get(f"/api/v1/alerts?vendor_id={vendor_id}&is_read=false")
        assert res_unread_after.json()["total"] == 1
