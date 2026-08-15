import uuid
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import AsyncSessionLocal, init_db_connection
from app.models.vendor import Vendor, RiskTier, VendorStatus
from app.models.document import Document, PolicyVersion
from app.schemas.risk import RiskFindingSchema, AIAssessmentResultSchema
from app.services.risk_engine import AIRiskEngine


@pytest.mark.asyncio
async def test_analyze_vendor_risk_api_flow():
    await init_db_connection()

    unique_domain = f"acme-{uuid.uuid4().hex[:8]}.com"
    vendor_url = f"https://{unique_domain}"

    async with AsyncSessionLocal() as session:
        # Create Vendor
        vendor = Vendor(
            name="Acme Security Cloud",
            domain=unique_domain,
            website_url=vendor_url,
            risk_tier=RiskTier.MEDIUM,
            current_risk_score=0.0,
            status=VendorStatus.ACTIVE
        )
        session.add(vendor)
        await session.commit()
        await session.refresh(vendor)
        vendor_id = vendor.id

        # Add Document & PolicyVersion
        doc1 = Document(
            vendor_id=vendor_id,
            document_type="Privacy Policy",
            title="Acme Privacy Policy",
            url=f"{vendor_url}/privacy",
            current_version_hash="hash123"
        )
        session.add(doc1)
        await session.commit()
        await session.refresh(doc1)

        policy_ver1 = PolicyVersion(
            document_id=doc1.id,
            version_number=1,
            content_hash="hash123",
            raw_content="We retain customer personal data for up to 5 years following contract expiration."
        )
        session.add(policy_ver1)

        doc2 = Document(
            vendor_id=vendor_id,
            document_type="Terms of Service",
            title="Acme Terms of Service",
            url=f"{vendor_url}/terms",
            current_version_hash="hash456"
        )
        session.add(doc2)
        await session.commit()
        await session.refresh(doc2)

        policy_ver2 = PolicyVersion(
            document_id=doc2.id,
            version_number=1,
            content_hash="hash456",
            raw_content="Maximum liability under any claim shall not exceed the total fees paid in the past 3 months."
        )
        session.add(policy_ver2)
        await session.commit()

    # Mock AI LLM structured response
    mock_ai_result = AIAssessmentResultSchema(
        summary="Vendor presents moderate risk due to 5-year privacy data retention and liability limitations.",
        findings=[
            RiskFindingSchema(
                category="Privacy",
                finding="Customer data retained for 5 years after contract expiration",
                severity="High",
                evidence="We retain customer personal data for up to 5 years following contract expiration.",
                source_url=f"{vendor_url}/privacy",
                confidence=0.92,
                recommendation="Negotiate shorter data retention period upon termination."
            ),
            RiskFindingSchema(
                category="Legal",
                finding="Aggressive 3-month liability cap",
                severity="Medium",
                evidence="Maximum liability under any claim shall not exceed the total fees paid in the past 3 months.",
                source_url=f"{vendor_url}/terms",
                confidence=0.88,
                recommendation="Request standard 12-month liability cap."
            )
        ]
    )

    with patch.object(AIRiskEngine, "_call_llm", new=AsyncMock(return_value=mock_ai_result)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Trigger POST /api/v1/vendors/{vendor_id}/analyze
            res = await ac.post(f"/api/v1/vendors/{vendor_id}/analyze")
            assert res.status_code == 200, f"Error: {res.text}"

            data = res.json()
            assert data["vendor_id"] == vendor_id
            assert data["status"] == "Completed"
            assert data["summary"].startswith("Vendor presents moderate risk")

            # Check Category Scores:
            # Privacy: High (+35) -> 35.0
            # Legal: Medium (+20) -> 20.0
            # Security: 0.0
            # Compliance: 0.0
            # Overall Score: Privacy(35 * 0.3) + Legal(20 * 0.2) = 10.5 + 4.0 = 14.5 -> Low Risk Tier
            cat_scores = {c["category_name"]: c["score"] for c in data["category_scores"]}
            assert cat_scores["Privacy"] == 35.0
            assert cat_scores["Legal"] == 20.0
            assert cat_scores["Security"] == 0.0
            assert cat_scores["Compliance"] == 0.0

            assert data["overall_score"] == 14.5
            assert data["risk_tier"] == "Low"

            # 2. Trigger GET /api/v1/vendors/{vendor_id}/risk-assessment
            get_res = await ac.get(f"/api/v1/vendors/{vendor_id}/risk-assessment")
            assert get_res.status_code == 200
            get_data = get_res.json()

            assert get_data["id"] == data["id"]
            assert get_data["overall_score"] == 14.5
            assert get_data["risk_tier"] == "Low"
            assert len(get_data["category_scores"]) == 4


@pytest.mark.asyncio
async def test_risk_api_error_handling():
    await init_db_connection()

    non_existent_id = str(uuid.uuid4())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Missing Vendor ID for POST analyze -> 404 Not Found
        res_post_404 = await ac.post(f"/api/v1/vendors/{non_existent_id}/analyze")
        assert res_post_404.status_code == 404
        assert "not found" in res_post_404.json()["detail"].lower()

        # 2. Missing Vendor ID for GET risk-assessment -> 404 Not Found
        res_get_404 = await ac.get(f"/api/v1/vendors/{non_existent_id}/risk-assessment")
        assert res_get_404.status_code == 404
        assert "not found" in res_get_404.json()["detail"].lower()

    # Create Vendor without PolicyVersion
    async with AsyncSessionLocal() as session:
        empty_vendor = Vendor(
            name="Empty Vendor",
            domain=f"empty-{uuid.uuid4().hex[:6]}.com",
            website_url="https://empty-vendor.com",
            risk_tier=RiskTier.MEDIUM,
            status=VendorStatus.ACTIVE
        )
        session.add(empty_vendor)
        await session.commit()
        await session.refresh(empty_vendor)
        empty_id = empty_vendor.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 3. GET risk-assessment for vendor without assessment -> 404 Not Found
        res_no_assessment = await ac.get(f"/api/v1/vendors/{empty_id}/risk-assessment")
        assert res_no_assessment.status_code == 404
        assert "no risk assessment found" in res_no_assessment.json()["detail"].lower()

        # 4. POST analyze for vendor without policy documents -> 400 Bad Request
        res_no_docs = await ac.post(f"/api/v1/vendors/{empty_id}/analyze")
        assert res_no_docs.status_code == 400
        assert "no stored policy document content" in res_no_docs.json()["detail"].lower()

    # Add Document with text to empty vendor
    async with AsyncSessionLocal() as session:
        doc = Document(
            vendor_id=empty_id,
            document_type="Privacy Policy",
            title="Privacy Policy",
            url="https://empty-vendor.com/privacy"
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        ver = PolicyVersion(
            document_id=doc.id,
            version_number=1,
            content_hash="h1",
            raw_content="Privacy policy text."
        )
        session.add(ver)
        await session.commit()

    # 5. LLM API Exception handling -> 502 Bad Gateway
    with patch.object(AIRiskEngine, "_call_llm", new=AsyncMock(side_effect=RuntimeError("OpenAI API rate limit exceeded"))):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res_llm_err = await ac.post(f"/api/v1/vendors/{empty_id}/analyze")
            assert res_llm_err.status_code == 502
            assert "openai api rate limit exceeded" in res_llm_err.json()["detail"].lower()

