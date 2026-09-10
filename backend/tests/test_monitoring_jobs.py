import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from app.main import app
from app.core.database import AsyncSessionLocal, init_db_connection
from app.models.vendor import Vendor, VendorStatus, MonitoringFrequency
from app.services.crawler import VendorCrawlerService
from app.services.monitoring_job_manager import (
    get_monitoring_job_store,
    run_monitoring_job_task,
    MonitoringJob,
)


@pytest.mark.asyncio
async def test_monitoring_trigger_endpoint_returns_202_and_job_id():
    """Verify POST /api/v1/monitoring/trigger returns HTTP 202 with job_id and pending status."""
    await init_db_connection()
    mock_crawl = {
        "vendor_domain": "test.com",
        "normalized_start_url": "https://test.com",
        "documents": []
    }
    with patch.object(VendorCrawlerService, "crawl_vendor", new=AsyncMock(return_value=mock_crawl)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/v1/monitoring/trigger?force=true")
            assert res.status_code == 202, f"Expected 202, got {res.status_code}: {res.text}"
            data = res.json()
            assert "job_id" in data
            assert uuid.UUID(data["job_id"])  # Valid UUID
            assert data["status"] in ("pending", "completed")
            assert data["message"] == "Monitoring job accepted"
            assert isinstance(data["total_vendors"], int)


@pytest.mark.asyncio
async def test_monitoring_job_status_not_found():
    """Verify GET /api/v1/monitoring/jobs/{job_id} returns 404 for unknown job_id."""
    await init_db_connection()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        fake_id = str(uuid.uuid4())
        res = await ac.get(f"/api/v1/monitoring/jobs/{fake_id}")
        assert res.status_code == 404
        assert f"Monitoring job '{fake_id}' not found" in res.json()["detail"]


@pytest.mark.asyncio
async def test_monitoring_job_lifecycle_to_completion():
    """Verify background monitoring job executes and transitions to completed with valid counts."""
    await init_db_connection()

    unique_domain = f"job-test-{uuid.uuid4().hex[:8]}.com"
    target_url = f"https://{unique_domain}"

    async with AsyncSessionLocal() as session:
        vendor = Vendor(
            name="Job Test Vendor",
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
            trigger_res = await ac.post(f"/api/v1/monitoring/trigger?vendor_id={vendor_id}&force=true")
            assert trigger_res.status_code == 202
            job_id = trigger_res.json()["job_id"]

            status_res = await ac.get(f"/api/v1/monitoring/jobs/{job_id}")
            assert status_res.status_code == 200
            st_data = status_res.json()
            assert st_data["job_id"] == job_id
            # ASGITransport executes background tasks inline before response completion
            assert st_data["status"] == "completed"
            assert st_data["total_vendors"] == 1
            assert st_data["completed_vendors"] == 1
            assert st_data["successful_vendors"] == 1
            assert st_data["failed_vendors"] == 0
            assert st_data["completed_at"] is not None


@pytest.mark.asyncio
async def test_single_vendor_failure_isolation_in_job():
    """Verify that if one vendor fails during monitoring, subsequent vendors still process and job completes."""
    await init_db_connection()

    v1_domain = f"v1-iso-{uuid.uuid4().hex[:8]}.com"
    v2_domain = f"v2-iso-{uuid.uuid4().hex[:8]}.com"

    async with AsyncSessionLocal() as session:
        v1 = Vendor(
            name="Failing Vendor",
            domain=v1_domain,
            website_url=f"https://{v1_domain}",
            monitoring_frequency=MonitoringFrequency.DAILY,
            status=VendorStatus.ACTIVE
        )
        v2 = Vendor(
            name="Succeeding Vendor",
            domain=v2_domain,
            website_url=f"https://{v2_domain}",
            monitoring_frequency=MonitoringFrequency.DAILY,
            status=VendorStatus.ACTIVE
        )
        session.add_all([v1, v2])
        await session.commit()
        await session.refresh(v1)
        await session.refresh(v2)
        v1_id, v2_id = v1.id, v2.id

    async def mock_crawl(url: str):
        if v1_domain in url:
            raise RuntimeError("Simulated network timeout for vendor 1")
        return {
            "vendor_domain": v2_domain,
            "normalized_start_url": f"https://{v2_domain}",
            "documents": []
        }

    job_store = get_monitoring_job_store()
    job = job_store.create_job(total_vendors=2)

    with patch.object(VendorCrawlerService, "crawl_vendor", side_effect=mock_crawl):
        await run_monitoring_job_task(job_id=job.job_id, vendor_ids=[v1_id, v2_id], force=True)

    completed_job = job_store.get_job(job.job_id)
    assert completed_job is not None
    assert completed_job.status == "completed"
    assert completed_job.total_vendors == 2
    assert completed_job.completed_vendors == 2
    assert completed_job.successful_vendors == 1
    assert completed_job.failed_vendors == 1
    assert completed_job.completed_at is not None


@pytest.mark.asyncio
async def test_monitoring_job_zero_vendors():
    """Verify handling when zero vendors are provided or due."""
    job_store = get_monitoring_job_store()
    job = job_store.create_job(total_vendors=0)

    await run_monitoring_job_task(job_id=job.job_id, vendor_ids=[])

    completed_job = job_store.get_job(job.job_id)
    assert completed_job is not None
    assert completed_job.status == "completed"
    assert completed_job.total_vendors == 0
    assert completed_job.completed_vendors == 0
    assert completed_job.successful_vendors == 0
    assert completed_job.failed_vendors == 0
    assert completed_job.completed_at is not None
