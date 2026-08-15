import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal, init_db_connection
from app.models.vendor import Vendor, RiskTier, VendorStatus, MonitoringFrequency
from app.models.document import Document, PolicyVersion
from app.models.risk import RiskAssessment, CategoryScore
from app.models.alert import Alert
from app.models.audit import AuditLog


@pytest.mark.asyncio
async def test_db_init_and_vendor_crud():
    await init_db_connection()
    
    unique_domain = f"slack-{uuid.uuid4().hex[:8]}.com"
    async with AsyncSessionLocal() as session:
        # Create a Vendor
        vendor = Vendor(
            name="Slack Technologies",
            domain=unique_domain,
            industry="Productivity / Collaboration",
            website_url=f"https://{unique_domain}",
            risk_tier=RiskTier.LOW,
            current_risk_score=15.5,
            status=VendorStatus.ACTIVE,
            monitoring_frequency=MonitoringFrequency.DAILY
        )
        session.add(vendor)
        await session.commit()
        await session.refresh(vendor)

        assert vendor.id is not None
        assert vendor.domain == unique_domain
        assert vendor.created_at is not None

        # Add Document to Vendor
        doc = Document(
            vendor_id=vendor.id,
            document_type="Privacy Policy",
            title="Slack Privacy Policy 2026",
            url="https://slack.com/privacy-policy",
            current_version_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        assert doc.id is not None
        assert doc.vendor_id == vendor.id

        # Add Risk Assessment
        assessment = RiskAssessment(
            vendor_id=vendor.id,
            overall_score=15.5,
            risk_tier="Low",
            summary="Strong encryption and SOC2 Type II compliance.",
            key_findings=["TLS 1.3 enforced", "GDPR compliant data handling"],
            citations=["Privacy Policy Section 4"],
            status="Completed"
        )
        session.add(assessment)
        await session.commit()
        await session.refresh(assessment)

        # Add Category Score
        cat_score = CategoryScore(
            assessment_id=assessment.id,
            category_name="Privacy",
            score=12.0,
            justification="Clear retention period and zero unconsented data sales.",
            findings=["Explicit opt-out provided"]
        )
        session.add(cat_score)

        # Add Alert
        alert = Alert(
            vendor_id=vendor.id,
            alert_type="Policy Change",
            severity="Low",
            title="Privacy Policy Section 3 Updated",
            description="Minor wording update detected in sub-processor list."
        )
        session.add(alert)

        # Add Audit Log
        audit = AuditLog(
            vendor_id=vendor.id,
            action="VENDOR_CREATED",
            actor="Admin",
            details={"domain": "slack.com"}
        )
        session.add(audit)

        await session.commit()

        # Query back Vendor with relationships loaded via selectinload
        from sqlalchemy.orm import selectinload
        stmt = (
            select(Vendor)
            .options(
                selectinload(Vendor.documents),
                selectinload(Vendor.risk_assessments),
                selectinload(Vendor.alerts),
                selectinload(Vendor.audit_logs)
            )
            .where(Vendor.id == vendor.id)
        )
        res = await session.execute(stmt)
        queried_vendor = res.scalar_one()

        assert len(queried_vendor.documents) == 1
        assert len(queried_vendor.risk_assessments) == 1
        assert len(queried_vendor.alerts) == 1
        assert len(queried_vendor.audit_logs) == 1
