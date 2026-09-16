import uuid
import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from app.core.database import Base, get_db
from app.main import app
from app.models.vendor import Vendor, RiskTier, VendorStatus, MonitoringFrequency
from app.models.document import Document, PolicyVersion
from app.models.compliance import ComplianceAssessment, ComplianceStatus
from app.models.document_chunk import DocumentChunk
from app.schemas.compliance import ComplianceAssessmentResult, ComplianceFrameworkSummarySchema
from app.services.compliance.catalog import COMPLIANCE_CATALOG, get_catalog_by_framework
from app.services.compliance.service import compliance_service

@pytest_asyncio.fixture
async def async_test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    TestingSessionLocal = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture
def mock_app(async_test_db):
    async def override_get_db():
        yield async_test_db
    app.dependency_overrides[get_db] = override_get_db
    yield app
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_control_catalog_valid():
    """Test control catalog is valid and framework filtering works"""
    assert len(COMPLIANCE_CATALOG) > 0
    
    for fw in set([c.framework for c in COMPLIANCE_CATALOG]):
        fw_controls = get_catalog_by_framework(fw)
        assert len(fw_controls) > 0
        ids = [c.control_id for c in fw_controls]
        assert len(ids) == len(set(ids))

    soc2 = get_catalog_by_framework("SOC 2 Type II")
    assert len(soc2) > 0
    for control in soc2:
        assert control.framework == "SOC 2 Type II"
        assert control.control_id
        assert control.control_title

@pytest.mark.asyncio
async def test_get_compliance_invalid_vendor(async_test_db):
    """Test API response for invalid vendor"""
    with pytest.raises(ValueError) as excinfo:
        await compliance_service.get_or_compute_compliance(async_test_db, "nonexistent-id")
    assert "not found" in str(excinfo.value).lower()

@pytest.mark.asyncio
async def test_api_compliance_flow_and_cache(mock_app, async_test_db):
    """Test the API endpoints, evaluation rules (PASS, PARTIAL, GAP, NOT_ASSESSED, caching)"""
    vendor = Vendor(
        id=str(uuid.uuid4()),
        name="Test Compliance Vendor",
        domain="compliance.test",
        website_url="https://compliance.test",
        risk_tier=RiskTier.LOW,
        status=VendorStatus.ACTIVE,
        monitoring_frequency=MonitoringFrequency.DAILY
    )
    doc = Document(
        id=str(uuid.uuid4()),
        vendor_id=vendor.id,
        document_type="Privacy Policy",
        title="Privacy Policy",
        url="https://compliance.test/privacy"
    )
    policy = PolicyVersion(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        version_number=1,
        content_hash="abc",
        raw_content="We encrypt all data. We don't have access control. Data is retained forever."
    )
    chunk = DocumentChunk(
        id=str(uuid.uuid4()),
        vendor_id=vendor.id,
        document_id=doc.id,
        policy_version_id=policy.id,
        chunk_index=0,
        text="We encrypt all data. We don't have access control. Data is retained forever.",
        content_hash="abc"
    )
    async_test_db.add_all([vendor, doc, policy, chunk])
    await async_test_db.commit()

    # Mock RAG Retriever
    mock_retrieval_result = MagicMock()
    mock_retrieval_result.source_url = doc.url
    mock_retrieval_result.document_id = doc.id
    mock_retrieval_result.policy_version_id = policy.id
    mock_retrieval_result.text = chunk.text

    # Mock LLM Service responses for different statuses
    def mock_analyze_control(**kwargs):
        ctrl = kwargs["control_id"]
        res = ComplianceAssessmentResult(
            framework=kwargs["control_framework"],
            control_id=ctrl,
            control_title=kwargs["control_title"],
            status="NOT_ASSESSED",
            confidence=0.9
        )
        if "CC6.1" in ctrl:  # Security / Access Control - Explicit contradiction -> GAP
            res.status = "GAP"
            res.evidence_quote = "We don't have access control."
            res.gap_reason = "Explicitly states no access control."
            res.source_url = doc.url
        elif "Art. 32" in ctrl:  # Security of processing (Encryption) -> PASS
            res.status = "PASS"
            res.evidence_quote = "We encrypt all data."
            res.source_url = doc.url
        elif "Art. 17" in ctrl: # Right to erasure -> GAP
            res.status = "GAP"
            res.evidence_quote = "Data is retained forever."
            res.source_url = doc.url
        elif "CC1.1" in ctrl: # Ethics - missing -> NOT_ASSESSED
            res.status = "NOT_ASSESSED"
            res.gap_reason = "No evidence found"
        elif "invalid_quote" in ctrl: # Test verification failure
            res.status = "PASS"
            res.evidence_quote = "This quote is entirely invented by the LLM."
            res.source_url = doc.url
        else:
            res.status = "PARTIAL"
            res.evidence_quote = "We encrypt all data."
            res.source_url = doc.url

        return res

    with patch("app.services.rag.retriever.RAGRetriever.search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = [mock_retrieval_result]
        
        # Patch the specific service instance used by the compliance_service
        with patch.object(compliance_service.llm_service, "analyze_compliance_control", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.side_effect = mock_analyze_control
            
            async with AsyncClient(transport=ASGITransport(app=mock_app), base_url="http://test") as ac:
                # Test 1: Generate initial assessment
                res = await ac.get(f"/api/v1/vendors/{vendor.id}/compliance")
                assert res.status_code == 200
                data = res.json()
                assert len(data["summaries"]) > 0
                assert len(data["assessments"]) > 0
                
                # Verify RAG and LLM were called
                assert mock_search.call_count > 0
                assert mock_analyze.call_count > 0
                
                llm_calls_first_run = mock_analyze.call_count
                
                # Check specific statuses
                assessments = data["assessments"]
                cc61 = next(a for a in assessments if a["control_id"] == "CC6.1")
                assert cc61["status"] == "GAP"
                
                art32 = next(a for a in assessments if a["control_id"] == "Art. 32")
                assert art32["status"] == "PASS"
                assert art32["source_url"] == doc.url
                
                cc11 = next(a for a in assessments if a["control_id"] == "CC1.1")
                assert cc11["status"] == "NOT_ASSESSED"
                
                # Test 2: Cache Hit
                res2 = await ac.get(f"/api/v1/vendors/{vendor.id}/compliance")
                assert res2.status_code == 200
                assert mock_analyze.call_count == llm_calls_first_run # NO additional LLM calls
                
                # Test 3: Framework Filtering
                res_soc2 = await ac.get(f"/api/v1/vendors/{vendor.id}/compliance?framework=SOC 2 Type II")
                assert res_soc2.status_code == 200
                soc2_data = res_soc2.json()
                for a in soc2_data["assessments"]:
                    assert a["framework"] == "SOC 2 Type II"
                    
                # Test 4: Status Filtering
                res_pass = await ac.get(f"/api/v1/vendors/{vendor.id}/compliance?status=PASS")
                assert res_pass.status_code == 200
                pass_data = res_pass.json()
                for a in pass_data["assessments"]:
                    assert a["status"] == "PASS"

                # Test 5: Cache Invalidation
                # We simulate a new policy version being crawled
                import asyncio
                await asyncio.sleep(0.1) # small delay to ensure crawled_at > assessed_at
                from datetime import datetime, timezone
                new_policy = PolicyVersion(
                    id=str(uuid.uuid4()),
                    document_id=doc.id,
                    version_number=2,
                    content_hash="def",
                    raw_content="New content",
                    crawled_at=datetime.now(timezone.utc)
                )
                async_test_db.add(new_policy)
                await async_test_db.commit()

                res_invalidate = await ac.get(f"/api/v1/vendors/{vendor.id}/compliance")
                assert res_invalidate.status_code == 200
                # LLM should be called again because cache was invalidated
                assert mock_analyze.call_count > llm_calls_first_run

@pytest.mark.asyncio
async def test_evidence_verification_failure(async_test_db):
    """Test that LLM inventing quotes downgrades PASS to NOT_ASSESSED"""
    vendor = Vendor(
        id=str(uuid.uuid4()),
        name="Verification Test",
        domain="verify.test",
        website_url="https://verify.test",
        risk_tier=RiskTier.LOW,
        status=VendorStatus.ACTIVE,
        monitoring_frequency=MonitoringFrequency.DAILY
    )
    async_test_db.add(vendor)
    await async_test_db.commit()

    # Mock RAG Retriever
    mock_retrieval_result = MagicMock()
    mock_retrieval_result.source_url = "https://url"
    mock_retrieval_result.document_id = "doc1"
    mock_retrieval_result.policy_version_id = "v1"
    mock_retrieval_result.text = "Actual policy text here."

    def mock_analyze_control(**kwargs):
        res = ComplianceAssessmentResult(
            framework=kwargs["control_framework"],
            control_id=kwargs["control_id"],
            control_title=kwargs["control_title"],
            status="PASS",
            confidence=0.9,
            evidence_quote="Fake quote invented by LLM.", # DOES NOT MATCH TEXT
            source_url="https://url"
        )
        return res

    with patch("app.services.rag.retriever.RAGRetriever.search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = [mock_retrieval_result]
        with patch.object(compliance_service.llm_service, "analyze_compliance_control", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.side_effect = mock_analyze_control
            
            response = await compliance_service.get_or_compute_compliance(async_test_db, vendor.id, "SOC 2 Type II")
            
            # The PASS should have been downgraded to NOT_ASSESSED due to validation failure
            for assessment in response.assessments:
                assert assessment.status == "NOT_ASSESSED"
                assert assessment.evidence_quote is None
                assert "invalid evidence quote" in assessment.gap_reason
