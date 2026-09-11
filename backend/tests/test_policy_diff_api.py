import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import AsyncSessionLocal, init_db_connection
from app.models.vendor import Vendor, RiskTier, VendorStatus, MonitoringFrequency
from app.models.document import Document, PolicyVersion
from app.models.policy_diff import PolicyDiff


@pytest.mark.asyncio
async def test_versions_vendor_not_found():
    await init_db_connection()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        fake_vendor_id = str(uuid.uuid4())
        fake_doc_id = str(uuid.uuid4())
        res = await ac.get(f"/api/v1/vendors/{fake_vendor_id}/documents/{fake_doc_id}/versions")
        assert res.status_code == 404
        assert f"Vendor with ID '{fake_vendor_id}' not found" in res.json()["detail"]


@pytest.mark.asyncio
async def test_versions_document_not_found():
    await init_db_connection()
    unique_domain = f"test-diff-{uuid.uuid4().hex[:8]}.com"

    async with AsyncSessionLocal() as session:
        vendor = Vendor(
            name="DiffCorp",
            domain=unique_domain,
            website_url=f"https://{unique_domain}",
            risk_tier=RiskTier.LOW,
            current_risk_score=25.0,
            status=VendorStatus.ACTIVE,
            monitoring_frequency=MonitoringFrequency.WEEKLY,
        )
        session.add(vendor)
        await session.commit()
        await session.refresh(vendor)
        vendor_id = vendor.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        fake_doc_id = str(uuid.uuid4())
        res = await ac.get(f"/api/v1/vendors/{vendor_id}/documents/{fake_doc_id}/versions")
        assert res.status_code == 404
        assert f"Document with ID '{fake_doc_id}' not found" in res.json()["detail"]


@pytest.mark.asyncio
async def test_versions_wrong_document_owner():
    await init_db_connection()
    dom_a = f"test-a-{uuid.uuid4().hex[:8]}.com"
    dom_b = f"test-b-{uuid.uuid4().hex[:8]}.com"

    async with AsyncSessionLocal() as session:
        vendor_a = Vendor(name="A", domain=dom_a, website_url=f"https://{dom_a}")
        vendor_b = Vendor(name="B", domain=dom_b, website_url=f"https://{dom_b}")
        session.add_all([vendor_a, vendor_b])
        await session.commit()
        await session.refresh(vendor_a)
        await session.refresh(vendor_b)

        doc_b = Document(
            vendor_id=vendor_b.id,
            document_type="Privacy Policy",
            title="B Privacy",
            url=f"https://{dom_b}/privacy",
        )
        session.add(doc_b)
        await session.commit()
        await session.refresh(doc_b)

        v_a_id = vendor_a.id
        doc_b_id = doc_b.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/vendors/{v_a_id}/documents/{doc_b_id}/versions")
        assert res.status_code == 400
        assert "does not belong to vendor" in res.json()["detail"]


@pytest.mark.asyncio
async def test_versions_and_diff_workflow_with_caching():
    await init_db_connection()
    unique_domain = f"test-flow-{uuid.uuid4().hex[:8]}.com"
    now_utc = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        vendor = Vendor(
            name="FlowCorp",
            domain=unique_domain,
            website_url=f"https://{unique_domain}",
            risk_tier=RiskTier.MEDIUM,
            current_risk_score=45.0,
            status=VendorStatus.ACTIVE,
        )
        session.add(vendor)
        await session.commit()
        await session.refresh(vendor)

        doc = Document(
            vendor_id=vendor.id,
            document_type="Terms of Service",
            title="Master Services Agreement",
            url=f"https://{unique_domain}/terms",
            current_version_hash="hash2",
            last_crawled_at=now_utc,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        v1_content = (
            "1. Introduction: Welcome to FlowCorp.\n"
            "2. Data Privacy: We never sell your personal data.\n"
            "3. Liability: FlowCorp's maximum liability is limited to $10,000.\n"
            "4. Jurisdiction: Governed by the laws of California."
        )
        v2_content = (
            "1. Introduction: Welcome to FlowCorp Inc.\n"
            "2. Data Privacy: We may share user telemetry with select partners.\n"
            "2.1 AI Usage: Customer queries may be used to train AI models.\n"
            "3. Liability: FlowCorp disclaims all indirect and incidental damages.\n"
            "4. Jurisdiction: Mandatory arbitration in Delaware."
        )

        ver1 = PolicyVersion(
            document_id=doc.id,
            version_number=1,
            content_hash="hash1",
            raw_content=v1_content,
            summary="Initial version",
            crawled_at=now_utc,
        )
        ver2 = PolicyVersion(
            document_id=doc.id,
            version_number=2,
            content_hash="hash2",
            raw_content=v2_content,
            summary="Updated version with AI clauses",
            crawled_at=now_utc,
        )
        session.add_all([ver1, ver2])
        await session.commit()
        await session.refresh(ver1)
        await session.refresh(ver2)

        v_id = vendor.id
        d_id = doc.id
        v1_id = ver1.id
        v2_id = ver2.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Test GET versions
        res_ver = await ac.get(f"/api/v1/vendors/{v_id}/documents/{d_id}/versions")
        assert res_ver.status_code == 200
        ver_data = res_ver.json()
        assert len(ver_data) == 2
        assert ver_data[0]["version_number"] == 2
        assert ver_data[1]["version_number"] == 1
        assert ver_data[0]["line_count"] > 0

        # 2. Test GET diff for identical versions (v1 vs v1)
        res_same = await ac.get(
            f"/api/v1/vendors/{v_id}/documents/{d_id}/diff?v1={v1_id}&v2={v1_id}"
        )
        assert res_same.status_code == 200
        same_data = res_same.json()
        assert same_data["deterministic_diff"]["stats"]["is_identical"] is True
        assert same_data["semantic_impact"]["materiality"] == "Low"
        assert same_data["semantic_impact"]["risk_posture"] == "Neutral"

        # 3. Test GET diff first time (uncached)
        res_diff = await ac.get(
            f"/api/v1/vendors/{v_id}/documents/{d_id}/diff?v1={v1_id}&v2={v2_id}"
        )
        assert res_diff.status_code == 200
        diff_data = res_diff.json()
        assert diff_data["is_cached"] is False
        assert diff_data["vendor_name"] == "FlowCorp"
        assert diff_data["deterministic_diff"]["stats"]["added_lines"] > 0
        assert diff_data["deterministic_diff"]["stats"]["deleted_lines"] > 0
        assert len(diff_data["deterministic_diff"]["unified_hunks"]) > 0
        assert len(diff_data["deterministic_diff"]["side_by_side_rows"]) > 0
        assert diff_data["semantic_impact"]["materiality"] in ["Low", "Medium", "High", "Critical"]
        assert diff_data["semantic_impact"]["risk_posture"] in ["Favorable", "Neutral", "Adverse"]

        # 4. Test GET diff second time (should be cached!)
        res_cached = await ac.get(
            f"/api/v1/vendors/{v_id}/documents/{d_id}/diff?v1={v1_id}&v2={v2_id}"
        )
        assert res_cached.status_code == 200
        cached_data = res_cached.json()
        assert cached_data["is_cached"] is True
        assert cached_data["semantic_impact"]["executive_change_summary"] == diff_data["semantic_impact"]["executive_change_summary"]


@pytest.mark.asyncio
async def test_diff_invalid_version_ids():
    await init_db_connection()
    unique_domain = f"test-inv-{uuid.uuid4().hex[:8]}.com"

    async with AsyncSessionLocal() as session:
        vendor = Vendor(name="InvCorp", domain=unique_domain, website_url=f"https://{unique_domain}")
        session.add(vendor)
        await session.commit()
        await session.refresh(vendor)

        doc = Document(vendor_id=vendor.id, document_type="Privacy", title="Privacy", url=f"https://{unique_domain}/p")
        session.add(doc)
        await session.commit()
        await session.refresh(doc)
        v_id = vendor.id
        d_id = doc.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        fake_v1 = str(uuid.uuid4())
        fake_v2 = str(uuid.uuid4())
        res = await ac.get(f"/api/v1/vendors/{v_id}/documents/{d_id}/diff?v1={fake_v1}&v2={fake_v2}")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()
