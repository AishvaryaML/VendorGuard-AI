import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import AsyncSessionLocal, init_db_connection
from app.models.vendor import Vendor, RiskTier, VendorStatus, MonitoringFrequency
from app.models.document import Document, PolicyVersion
from app.models.risk import RiskAssessment, CategoryScore


@pytest.mark.asyncio
async def test_report_vendor_not_found():
    """Verify 404 is returned when requesting report for a nonexistent vendor ID."""
    await init_db_connection()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        fake_id = str(uuid.uuid4())
        res = await ac.get(f"/api/v1/vendors/{fake_id}/report")
        assert res.status_code == 404
        assert f"Vendor with ID '{fake_id}' not found" in res.json()["detail"]

        res_md = await ac.get(f"/api/v1/vendors/{fake_id}/report/markdown")
        assert res_md.status_code == 404

        res_pdf = await ac.get(f"/api/v1/vendors/{fake_id}/report/pdf")
        assert res_pdf.status_code == 404


@pytest.mark.asyncio
async def test_structured_vendor_security_report():
    """Verify structured report contains all vendor, risk, findings, evidence, and recommendations data."""
    await init_db_connection()

    unique_domain = f"test-report-{uuid.uuid4().hex[:8]}.com"
    target_url = f"https://{unique_domain}"
    now_utc = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        vendor = Vendor(
            name="ReportCorp Inc",
            domain=unique_domain,
            website_url=target_url,
            risk_tier=RiskTier.HIGH,
            current_risk_score=62.5,
            status=VendorStatus.ACTIVE,
            monitoring_frequency=MonitoringFrequency.WEEKLY,
            last_monitored_at=now_utc
        )
        session.add(vendor)
        await session.commit()
        await session.refresh(vendor)

        doc = Document(
            vendor_id=vendor.id,
            document_type="Privacy Policy",
            title="General Privacy Statement",
            url=f"{target_url}/privacy",
            current_version_hash="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            last_crawled_at=now_utc
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        ver = PolicyVersion(
            document_id=doc.id,
            version_number=1,
            content_hash=doc.current_version_hash,
            raw_content="We collect personal data and retain records for 7 years.",
            change_summary="Initial policy document content captured.",
            crawled_at=now_utc
        )
        session.add(ver)

        assessment = RiskAssessment(
            vendor_id=vendor.id,
            assessment_date=now_utc,
            overall_score=62.5,
            risk_tier="High",
            summary="ReportCorp maintains data retention but lacks explicit cookie opt-out.",
            status="Completed",
            citations=[
                {
                    "category": "Privacy",
                    "document_type": "Privacy Policy",
                    "title": "General Privacy Statement",
                    "source_url": f"{target_url}/privacy",
                    "snippet": "We collect personal data and retain records for 7 years.",
                    "similarity_score": 0.88
                }
            ]
        )
        session.add(assessment)
        await session.commit()
        await session.refresh(assessment)

        cs_privacy = CategoryScore(
            assessment_id=assessment.id,
            category_name="Privacy",
            score=65.0,
            justification="Data retention is 7 years without automated user deletion.",
            findings=[
                {
                    "category": "Privacy",
                    "severity": "High",
                    "finding": "Extended 7-year data retention without self-service erasure.",
                    "evidence": "We collect personal data and retain records for 7 years.",
                    "source_url": f"{target_url}/privacy",
                    "recommendation": "Implement self-service GDPR erasure workflow.",
                    "is_verified": True
                }
            ]
        )
        cs_security = CategoryScore(
            assessment_id=assessment.id,
            category_name="Security",
            score=60.0,
            justification="AES-256 enabled; audit logs retained for 90 days.",
            findings=[]
        )
        session.add_all([cs_privacy, cs_security])
        await session.commit()
        vendor_id = vendor.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/vendors/{vendor_id}/report")
        assert res.status_code == 200
        data = res.json()

        # Check Vendor Information
        assert data["vendor"]["name"] == "ReportCorp Inc"
        assert data["vendor"]["domain"] == unique_domain
        assert data["vendor"]["risk_tier"] == "High"
        assert data["vendor"]["current_risk_score"] == 62.5
        assert data["has_assessment_data"] is True

        # Check Executive Summary
        assert "ReportCorp maintains data retention" in data["executive_summary"]["summary_text"]
        assert data["executive_summary"]["overall_score"] == 62.5
        assert data["executive_summary"]["overall_risk_tier"] == "High"

        # Check Category Scores
        cat_names = [c["category"] for c in data["risk_overview"]]
        assert "Privacy" in cat_names
        assert "Security" in cat_names
        privacy_cat = next(c for c in data["risk_overview"] if c["category"] == "Privacy")
        assert privacy_cat["score"] == 65.0

        # Check Findings
        assert len(data["findings"]) == 1
        finding = data["findings"][0]
        assert finding["category"] == "Privacy"
        assert finding["severity"] == "High"
        assert "Extended 7-year data retention" in finding["finding"]
        assert "Implement self-service" in finding["recommendation"]
        assert finding["is_verified"] is True

        # Check Evidence
        assert len(data["evidence"]) >= 1
        assert "We collect personal data and retain records for 7 years." in data["evidence"][0]["quote"]
        assert data["evidence"][0]["source_url"] == f"{target_url}/privacy"

        # Check Policy Snapshots
        assert len(data["policy_snapshots"]) == 1
        assert data["policy_snapshots"][0]["document_type"] == "Privacy Policy"
        assert data["policy_snapshots"][0]["version_number"] == 1


@pytest.mark.asyncio
async def test_markdown_report_export():
    """Verify Markdown report endpoint returns 200, valid markdown content, and filename header."""
    await init_db_connection()

    unique_domain = f"test-md-{uuid.uuid4().hex[:8]}.com"
    target_url = f"https://{unique_domain}"
    now_utc = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        vendor = Vendor(
            name="MarkdownVendor Inc",
            domain=unique_domain,
            website_url=target_url,
            risk_tier=RiskTier.LOW,
            current_risk_score=15.0,
            status=VendorStatus.ACTIVE,
            monitoring_frequency=MonitoringFrequency.DAILY,
            last_monitored_at=now_utc
        )
        session.add(vendor)
        await session.commit()
        await session.refresh(vendor)

        doc = Document(
            vendor_id=vendor.id,
            document_type="Terms of Service",
            title="Terms of Service",
            url=f"{target_url}/terms",
            current_version_hash="112233445566778899aabbccddeeff00112233445566778899aabbccddeeff00",
            last_crawled_at=now_utc
        )
        session.add(doc)
        await session.commit()

        assessment = RiskAssessment(
            vendor_id=vendor.id,
            assessment_date=now_utc,
            overall_score=15.0,
            risk_tier="Low",
            summary="MarkdownVendor demonstrates excellent compliance and minimal risk.",
            status="Completed"
        )
        session.add(assessment)
        await session.commit()
        vendor_id = vendor.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/vendors/{vendor_id}/report/markdown")
        assert res.status_code == 200
        assert "text/markdown" in res.headers["content-type"]
        assert 'attachment; filename="vendorguard_markdownvendor_inc_security_report.md"' in res.headers["content-disposition"]

        md_text = res.text
        assert "# Executive Security Assessment Report: MarkdownVendor Inc" in md_text
        assert f"Primary Domain**: `{unique_domain}`" in md_text
        assert "15.0 / 100" in md_text
        assert "Low" in md_text
        assert "MarkdownVendor demonstrates excellent compliance" in md_text
        assert "Category Risk Overview" in md_text
        assert "Policy Snapshots & Hash Versioning" in md_text


@pytest.mark.asyncio
async def test_pdf_report_export():
    """Verify PDF report endpoint returns 200, application/pdf content-type, and valid PDF bytes."""
    await init_db_connection()

    unique_domain = f"test-pdf-{uuid.uuid4().hex[:8]}.com"
    target_url = f"https://{unique_domain}"
    now_utc = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        vendor = Vendor(
            name="PdfExport Corp",
            domain=unique_domain,
            website_url=target_url,
            risk_tier=RiskTier.MEDIUM,
            current_risk_score=35.0,
            status=VendorStatus.ACTIVE,
            monitoring_frequency=MonitoringFrequency.DAILY,
            last_monitored_at=now_utc
        )
        session.add(vendor)
        await session.commit()
        await session.refresh(vendor)

        doc = Document(
            vendor_id=vendor.id,
            document_type="Security Center",
            title="Enterprise Security Policy",
            url=f"{target_url}/security",
            current_version_hash="99887766554433221100aabbccddeeff99887766554433221100aabbccddeeff",
            last_crawled_at=now_utc
        )
        session.add(doc)
        await session.commit()

        assessment = RiskAssessment(
            vendor_id=vendor.id,
            assessment_date=now_utc,
            overall_score=35.0,
            risk_tier="Medium",
            summary="PdfExport Corp holds SOC 2 Type II with minor gaps in incident response timelines.",
            status="Completed"
        )
        session.add(assessment)
        await session.commit()
        vendor_id = vendor.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/vendors/{vendor_id}/report/pdf")
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert 'attachment; filename="vendorguard_pdfexport_corp_security_report.pdf"' in res.headers["content-disposition"]
        assert res.content.startswith(b"%PDF-")
        assert len(res.content) > 1000  # Valid non-trivial PDF


@pytest.mark.asyncio
async def test_unassessed_vendor_report_handling():
    """Verify that a vendor with documents but NO risk assessment generates a clean report without crashing."""
    await init_db_connection()

    unique_domain = f"test-unassessed-{uuid.uuid4().hex[:8]}.com"
    target_url = f"https://{unique_domain}"
    now_utc = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        vendor = Vendor(
            name="Unassessed Tech",
            domain=unique_domain,
            website_url=target_url,
            risk_tier=RiskTier.MEDIUM,
            current_risk_score=0.0,
            status=VendorStatus.ACTIVE,
            monitoring_frequency=MonitoringFrequency.DAILY,
            last_monitored_at=None
        )
        session.add(vendor)
        await session.commit()
        await session.refresh(vendor)

        doc = Document(
            vendor_id=vendor.id,
            document_type="Privacy Policy",
            title="Privacy Notice",
            url=f"{target_url}/privacy",
            current_version_hash="aabbccddeeff11223344556677889900aabbccddeeff11223344556677889900",
            last_crawled_at=now_utc
        )
        session.add(doc)
        await session.commit()
        vendor_id = vendor.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # JSON endpoint
        res = await ac.get(f"/api/v1/vendors/{vendor_id}/report")
        assert res.status_code == 200
        data = res.json()
        assert data["vendor"]["name"] == "Unassessed Tech"
        assert data["has_assessment_data"] is False
        assert "No formal risk assessment has been executed yet" in data["executive_summary"]["summary_text"]
        assert len(data["findings"]) == 0
        assert len(data["evidence"]) == 0
        assert len(data["policy_snapshots"]) == 1

        # Markdown endpoint
        res_md = await ac.get(f"/api/v1/vendors/{vendor_id}/report/markdown")
        assert res_md.status_code == 200
        assert "Unassessed Tech" in res_md.text

        # PDF endpoint
        res_pdf = await ac.get(f"/api/v1/vendors/{vendor_id}/report/pdf")
        assert res_pdf.status_code == 200
        assert res_pdf.content.startswith(b"%PDF-")


@pytest.mark.asyncio
async def test_multiple_vendors_report_isolation():
    """Verify that reports for two different vendors contain strictly isolated, vendor-specific data."""
    await init_db_connection()

    d1 = f"test-iso-a-{uuid.uuid4().hex[:8]}.com"
    d2 = f"test-iso-b-{uuid.uuid4().hex[:8]}.com"
    now_utc = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        v1 = Vendor(
            name="Alpha Corp",
            domain=d1,
            website_url=f"https://{d1}",
            risk_tier=RiskTier.LOW,
            current_risk_score=10.0,
            status=VendorStatus.ACTIVE,
            monitoring_frequency=MonitoringFrequency.DAILY,
        )
        v2 = Vendor(
            name="Beta Corp",
            domain=d2,
            website_url=f"https://{d2}",
            risk_tier=RiskTier.CRITICAL,
            current_risk_score=90.0,
            status=VendorStatus.ACTIVE,
            monitoring_frequency=MonitoringFrequency.DAILY,
        )
        session.add_all([v1, v2])
        await session.commit()
        await session.refresh(v1)
        await session.refresh(v2)

        # Assessment for v1
        a1 = RiskAssessment(
            vendor_id=v1.id,
            assessment_date=now_utc,
            overall_score=10.0,
            risk_tier="Low",
            summary="Alpha Corp is highly compliant with zero critical issues.",
            status="Completed",
            citations=[{
                "category": "Security",
                "document_type": "Security Policy",
                "title": "Alpha Security",
                "source_url": f"https://{d1}/security",
                "snippet": "Alpha quote: 2FA required for all staff.",
                "similarity_score": 0.95
            }]
        )
        # Assessment for v2
        a2 = RiskAssessment(
            vendor_id=v2.id,
            assessment_date=now_utc,
            overall_score=90.0,
            risk_tier="Critical",
            summary="Beta Corp sells unencrypted customer databases.",
            status="Completed",
            citations=[{
                "category": "Privacy",
                "document_type": "Privacy Statement",
                "title": "Beta Privacy",
                "source_url": f"https://{d2}/privacy",
                "snippet": "Beta quote: We sell data to third parties.",
                "similarity_score": 0.99
            }]
        )
        session.add_all([a1, a2])
        await session.commit()

        v1_id, v2_id = v1.id, v2.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r1 = (await ac.get(f"/api/v1/vendors/{v1_id}/report")).json()
        r2 = (await ac.get(f"/api/v1/vendors/{v2_id}/report")).json()

        # Check Alpha isolation
        assert r1["vendor"]["name"] == "Alpha Corp"
        assert "Alpha Corp is highly compliant" in r1["executive_summary"]["summary_text"]
        assert "Alpha quote" in r1["evidence"][0]["quote"]
        assert "Beta Corp" not in str(r1)
        assert "Beta quote" not in str(r1)

        # Check Beta isolation
        assert r2["vendor"]["name"] == "Beta Corp"
        assert "Beta Corp sells unencrypted" in r2["executive_summary"]["summary_text"]
        assert "Beta quote" in r2["evidence"][0]["quote"]
        assert "Alpha Corp" not in str(r2)
        assert "Alpha quote" not in str(r2)
