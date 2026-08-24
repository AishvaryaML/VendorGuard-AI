import uuid
from datetime import datetime, timezone, timedelta
import pytest
from unittest.mock import AsyncMock, patch

from app.core.database import AsyncSessionLocal, init_db_connection
from app.core.scheduler import SchedulerManager
from app.models.vendor import Vendor, RiskTier, VendorStatus, MonitoringFrequency
from app.models.document import Document, PolicyVersion
from app.models.risk import RiskAssessment, CategoryScore
from app.models.alert import Alert
from app.schemas.risk import RiskFindingSchema, AIAssessmentResultSchema
from app.services.crawler import VendorCrawlerService
from app.services.monitoring import (
    MonitoringService,
    is_vendor_due_for_monitoring,
    generate_policy_diff,
)


@pytest.mark.asyncio
async def test_scheduler_lifecycle():
    scheduler_mgr = SchedulerManager()
    assert scheduler_mgr is SchedulerManager()  # Singleton test

    scheduler_mgr.start()
    assert scheduler_mgr.is_running is True

    scheduler_mgr.shutdown()
    assert scheduler_mgr.is_running is False



def test_is_vendor_due_for_monitoring_frequencies():
    now = datetime.now(timezone.utc)

    # 1. Never monitored vendor -> always due
    vendor1 = Vendor(
        name="V1",
        domain="v1.com",
        website_url="https://v1.com",
        monitoring_frequency=MonitoringFrequency.DAILY,
        last_monitored_at=None
    )
    assert is_vendor_due_for_monitoring(vendor1, now) is True

    # 2. Daily frequency: monitored 10h ago -> NOT due
    vendor_daily_not_due = Vendor(
        name="V2",
        domain="v2.com",
        website_url="https://v2.com",
        monitoring_frequency=MonitoringFrequency.DAILY,
        last_monitored_at=now - timedelta(hours=10)
    )
    assert is_vendor_due_for_monitoring(vendor_daily_not_due, now) is False

    # 3. Daily frequency: monitored 25h ago -> DUE
    vendor_daily_due = Vendor(
        name="V3",
        domain="v3.com",
        website_url="https://v3.com",
        monitoring_frequency=MonitoringFrequency.DAILY,
        last_monitored_at=now - timedelta(hours=25)
    )
    assert is_vendor_due_for_monitoring(vendor_daily_due, now) is True

    # 4. Weekly frequency: monitored 5 days ago -> NOT due
    vendor_weekly_not_due = Vendor(
        name="V4",
        domain="v4.com",
        website_url="https://v4.com",
        monitoring_frequency=MonitoringFrequency.WEEKLY,
        last_monitored_at=now - timedelta(days=5)
    )
    assert is_vendor_due_for_monitoring(vendor_weekly_not_due, now) is False

    # 5. Weekly frequency: monitored 8 days ago -> DUE
    vendor_weekly_due = Vendor(
        name="V5",
        domain="v5.com",
        website_url="https://v5.com",
        monitoring_frequency=MonitoringFrequency.WEEKLY,
        last_monitored_at=now - timedelta(days=8)
    )
    assert is_vendor_due_for_monitoring(vendor_weekly_due, now) is True


def test_generate_policy_diff():
    old_text = "We retain data for 3 years.\nSecurity is maintained via AES-128."
    new_text = "We retain data for 7 years.\nSecurity is maintained via AES-256.\nAll servers are SOC2 compliant."

    diff_summary = generate_policy_diff(old_text, new_text)
    assert "+3 line(s) added" in diff_summary
    assert "-2 line(s) removed" in diff_summary


@pytest.mark.asyncio
async def test_unchanged_document_creates_no_version_no_alert_no_llm():
    await init_db_connection()

    unique_domain = f"unchanged-{uuid.uuid4().hex[:8]}.com"
    vendor_url = f"https://{unique_domain}"

    async with AsyncSessionLocal() as session:
        vendor = Vendor(
            name="Unchanged Vendor",
            domain=unique_domain,
            website_url=vendor_url,
            monitoring_frequency=MonitoringFrequency.DAILY,
            last_monitored_at=datetime.now(timezone.utc) - timedelta(hours=30)
        )
        session.add(vendor)
        await session.commit()
        await session.refresh(vendor)
        vendor_id = vendor.id

        doc = Document(
            vendor_id=vendor_id,
            document_type="Privacy Policy",
            title="Privacy Policy",
            url=f"{vendor_url}/privacy",
            current_version_hash="same_hash_123"
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        ver = PolicyVersion(
            document_id=doc.id,
            version_number=1,
            content_hash="same_hash_123",
            raw_content="Static privacy policy content text."
        )
        session.add(ver)
        await session.commit()

    # Mock crawler returning identical text & hash
    mock_crawl_data = {
        "vendor_domain": unique_domain,
        "normalized_start_url": vendor_url,
        "documents": [
            {
                "document_type": "Privacy Policy",
                "title": "Privacy Policy",
                "url": f"{vendor_url}/privacy",
                "clean_text": "Static privacy policy content text.",
                "content_hash": "same_hash_123"
            }
        ]
    }

    service = MonitoringService()

    with patch.object(VendorCrawlerService, "crawl_vendor", new=AsyncMock(return_value=mock_crawl_data)):
        with patch.object(service.risk_engine, "analyze_vendor", new=AsyncMock()) as mock_risk_call:
            async with AsyncSessionLocal() as session:
                res = await service.monitor_single_vendor(session, vendor_id, force=True)

                assert res["status"] == "Success"
                assert res["documents_checked"] == 1
                assert res["documents_changed"] == 0
                assert res["risk_reassessed"] is False
                assert res["alerts_generated"] == 0

                # Verify LLM / analyze_vendor was NOT called
                mock_risk_call.assert_not_called()

            # Verify in DB: still only 1 PolicyVersion and 0 Alerts
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select
                from sqlalchemy.orm import selectinload

                doc_stmt = select(Document).options(selectinload(Document.versions)).where(Document.id == doc.id)
                doc_obj = (await session.execute(doc_stmt)).scalar_one()
                assert len(doc_obj.versions) == 1

                alert_stmt = select(Alert).where(Alert.vendor_id == vendor_id)
                alerts = (await session.execute(alert_stmt)).scalars().all()
                assert len(alerts) == 0


@pytest.mark.asyncio
async def test_changed_document_triggers_reassessment_and_degradation_alert():
    await init_db_connection()

    unique_domain = f"changed-{uuid.uuid4().hex[:8]}.com"
    vendor_url = f"https://{unique_domain}"

    async with AsyncSessionLocal() as session:
        vendor = Vendor(
            name="Changed Risk Vendor",
            domain=unique_domain,
            website_url=vendor_url,
            risk_tier=RiskTier.LOW,
            current_risk_score=15.0,
            monitoring_frequency=MonitoringFrequency.DAILY,
            last_monitored_at=datetime.now(timezone.utc) - timedelta(hours=30)
        )
        session.add(vendor)
        await session.commit()
        await session.refresh(vendor)
        vendor_id = vendor.id

        # Initial Document & PolicyVersion v1
        doc = Document(
            vendor_id=vendor_id,
            document_type="Privacy Policy",
            title="Privacy Policy",
            url=f"{vendor_url}/privacy",
            current_version_hash="old_hash_v1"
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        ver1 = PolicyVersion(
            document_id=doc.id,
            version_number=1,
            content_hash="old_hash_v1",
            raw_content="Data retained for 30 days."
        )
        session.add(ver1)

        # Initial Low Risk Assessment
        prev_assessment = RiskAssessment(
            vendor_id=vendor_id,
            overall_score=15.0,
            risk_tier="Low",
            summary="Initial Low Risk",
            status="Completed"
        )
        session.add(prev_assessment)
        await session.commit()
        await session.refresh(prev_assessment)

        cat1 = CategoryScore(
            assessment_id=prev_assessment.id,
            category_name="Privacy",
            score=15.0,
            justification="Low risk"
        )
        session.add(cat1)
        await session.commit()

    # Mock crawler returning NEW policy text (hash changed)
    mock_crawl_data = {
        "vendor_domain": unique_domain,
        "normalized_start_url": vendor_url,
        "documents": [
            {
                "document_type": "Privacy Policy",
                "title": "Privacy Policy",
                "url": f"{vendor_url}/privacy",
                "clean_text": "Data retained indefinitely and shared with third parties for marketing purposes.",
                "content_hash": "new_hash_v2"
            }
        ]
    }

    # Mock new AI Risk assessment with degraded score (Jump from 15 -> 65, Low -> High)
    mock_new_ai_result = AIAssessmentResultSchema(
        summary="Material risk increase due to indefinite retention and marketing data sharing.",
        findings=[
            RiskFindingSchema(
                category="Privacy",
                finding="Indefinite data retention and third party sharing",
                severity="Critical",
                evidence="Data retained indefinitely and shared with third parties for marketing purposes.",
                source_url=f"{vendor_url}/privacy",
                confidence=0.95,
                recommendation="Review data sharing agreements."
            )
        ]
    )

    service = MonitoringService()

    with patch.object(VendorCrawlerService, "crawl_vendor", new=AsyncMock(return_value=mock_crawl_data)):
        async with AsyncSessionLocal() as session:
            res = await service.monitor_single_vendor(
                db=session,
                vendor_id=vendor_id,
                force=True,
                mock_risk_result=mock_new_ai_result
            )

            assert res["status"] == "Success"
            assert res["documents_checked"] == 1
            assert res["documents_changed"] == 1
            assert res["risk_reassessed"] is True
            assert res["alerts_generated"] >= 2  # Policy Change Alert + Risk Degradation Alert

    # Verify DB state: new PolicyVersion v2 created & Risk Degradation Alert present
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        doc_stmt = select(Document).options(selectinload(Document.versions)).where(Document.id == doc.id)
        doc_obj = (await session.execute(doc_stmt)).scalar_one()
        assert len(doc_obj.versions) == 2
        assert doc_obj.versions[0].version_number == 2
        assert "Policy text updated" in doc_obj.versions[0].change_summary

        alert_stmt = select(Alert).where(Alert.vendor_id == vendor_id)
        alerts = (await session.execute(alert_stmt)).scalars().all()
        alert_types = [a.alert_type for a in alerts]
        assert "Policy Change" in alert_types
        assert "Risk Degradation" in alert_types

        deg_alert = next(a for a in alerts if a.alert_type == "Risk Degradation")
        assert deg_alert.severity in ["High", "Critical"]
        assert "Material risk degradation" in deg_alert.description


@pytest.mark.asyncio
async def test_vendor_failure_isolation():
    await init_db_connection()

    v1_domain = f"fail-{uuid.uuid4().hex[:6]}.com"
    v2_domain = f"success-{uuid.uuid4().hex[:6]}.com"

    async with AsyncSessionLocal() as session:
        v1 = Vendor(
            name="Failing Vendor",
            domain=v1_domain,
            website_url=f"https://{v1_domain}",
            monitoring_frequency=MonitoringFrequency.DAILY,
            last_monitored_at=datetime.now(timezone.utc) - timedelta(hours=30)
        )
        v2 = Vendor(
            name="Successful Vendor",
            domain=v2_domain,
            website_url=f"https://{v2_domain}",
            monitoring_frequency=MonitoringFrequency.DAILY,
            last_monitored_at=datetime.now(timezone.utc) - timedelta(hours=30)
        )
        session.add_all([v1, v2])
        await session.commit()
        await session.refresh(v1)
        await session.refresh(v2)

    service = MonitoringService()

    async def mock_crawl_side_effect(url, client=None):
        if v1_domain in url:
            raise RuntimeError("Connection timed out to vendor site")
        return {
            "vendor_domain": v2_domain,
            "normalized_start_url": f"https://{v2_domain}",
            "documents": []
        }

    with patch.object(VendorCrawlerService, "crawl_vendor", side_effect=mock_crawl_side_effect):
        async with AsyncSessionLocal() as session:
            results = await service.run_monitoring_cycle(db=session, force=True)

            # Find results for v1 and v2
            v1_res = next(r for r in results if r["vendor_id"] == v1.id)
            v2_res = next(r for r in results if r["vendor_id"] == v2.id)

            # Failing vendor fails cleanly without throwing uncaught exception
            assert v1_res["status"] == "Failed"
            assert "Connection timed out" in v1_res["error_detail"]

            # Successful vendor proceeds without interruption
            assert v2_res["status"] == "Success"
