import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import Base, get_db
from app.models.vendor import Vendor, RiskTier, VendorStatus, MonitoringFrequency
from app.models.document import Document, PolicyVersion
from app.schemas.risk import AIAssessmentResultSchema, RiskFindingSchema
from app.services.agents.discovery_agent import DiscoveryAgent
from app.services.agents.policy_auditor_agent import PolicyAuditorAgent
from app.services.agents.risk_auditor_agent import RiskAuditorAgent
from app.services.agents.executive_report_agent import ExecutiveReportAgent
from app.services.agents.graph import VendorRiskWorkflowRunner
from app.services.rag.embeddings import BaseEmbeddingService
from app.services.rag.vector_store import InMemoryVectorStore
from app.services.rag.indexer import RAGIndexer
from app.services.rag.retriever import RAGRetriever


class MockEmbeddingService(BaseEmbeddingService):
    @property
    def dimension(self) -> int:
        return 8

    async def embed_text(self, text: str):
        res = await self.embed_documents([text])
        return res[0]

    async def embed_documents(self, texts):
        return [[0.1] * 8 for _ in texts]


@pytest_asyncio.fixture
async def async_test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


# Helper to build mock AI risk findings matching verbatim policy text and source URL
def build_mock_assessment_result(domain: str, overall_risk: str = "Low", score: float = 10.0):
    if overall_risk == "Critical":
        findings = [
            RiskFindingSchema(
                category="Privacy",
                finding="Customer data sold to third party advertisers.",
                severity="Critical",
                evidence="We sell personal information to advertising networks.",
                source_url=f"https://{domain}/privacy",
                confidence=0.95,
                recommendation="Terminate vendor relationship immediately."
            ),
            RiskFindingSchema(
                category="Privacy",
                finding="Second critical privacy finding.",
                severity="Critical",
                evidence="We sell personal information to advertising networks.",
                source_url=f"https://{domain}/privacy",
                confidence=0.95,
                recommendation="Fix privacy."
            ),
            RiskFindingSchema(
                category="Security",
                finding="Unencrypted database backups.",
                severity="Critical",
                evidence="Backups are stored unencrypted.",
                source_url=f"https://{domain}/privacy",
                confidence=0.98,
                recommendation="Enforce encryption."
            ),
            RiskFindingSchema(
                category="Security",
                finding="Second critical security finding.",
                severity="Critical",
                evidence="Backups are stored unencrypted.",
                source_url=f"https://{domain}/privacy",
                confidence=0.98,
                recommendation="Fix security."
            ),
            RiskFindingSchema(
                category="Compliance",
                finding="Compliance failure.",
                severity="Critical",
                evidence="We sell personal information to advertising networks.",
                source_url=f"https://{domain}/privacy",
                confidence=0.95,
                recommendation="Fix compliance."
            ),
            RiskFindingSchema(
                category="Compliance",
                finding="Second compliance finding.",
                severity="Critical",
                evidence="We sell personal information to advertising networks.",
                source_url=f"https://{domain}/privacy",
                confidence=0.95,
                recommendation="Fix compliance."
            ),
            RiskFindingSchema(
                category="Legal",
                finding="Legal liability risk.",
                severity="Critical",
                evidence="Backups are stored unencrypted.",
                source_url=f"https://{domain}/privacy",
                confidence=0.95,
                recommendation="Fix legal."
            ),
            RiskFindingSchema(
                category="Legal",
                finding="Second legal finding.",
                severity="Critical",
                evidence="Backups are stored unencrypted.",
                source_url=f"https://{domain}/privacy",
                confidence=0.95,
                recommendation="Fix legal."
            )
        ]
    else:
        findings = [
            RiskFindingSchema(
                category="Privacy",
                finding="Minor cookie tracking without explicit banner.",
                severity="Low",
                evidence="We use cookies for site analytics.",
                source_url=f"https://{domain}/privacy",
                confidence=0.90,
                recommendation="Add cookie consent banner."
            )
        ]

    return AIAssessmentResultSchema(
        summary=f"Automated risk audit completed with {overall_risk} risk tier.",
        overall_risk_tier=overall_risk,
        overall_score=score,
        findings=findings
    )


def mock_crawl_data(domain: str, text: str):
    return {
        "vendor_domain": domain,
        "normalized_start_url": f"https://{domain}",
        "documents": [
            {
                "document_type": "Privacy Policy",
                "title": "Privacy Policy",
                "url": f"https://{domain}/privacy",
                "clean_text": text,
                "content_hash": "hash-" + domain
            }
        ]
    }


def create_test_runner(domain: str, text: str, mock_emb, vec_store):
    mock_crawler = MagicMock()
    mock_crawler.crawl_vendor = AsyncMock(return_value=mock_crawl_data(domain, text))

    indexer = RAGIndexer(embedding_service=mock_emb, vector_store=vec_store)
    retriever = RAGRetriever(embedding_service=mock_emb, vector_store=vec_store, indexer=indexer)

    return VendorRiskWorkflowRunner(
        discovery_agent=DiscoveryAgent(crawler_service=mock_crawler),
        policy_auditor_agent=PolicyAuditorAgent(indexer=indexer, retriever=retriever),
        risk_auditor_agent=RiskAuditorAgent(),
        executive_report_agent=ExecutiveReportAgent()
    )


# 1. Low-risk workflow completes automatically
@pytest.mark.asyncio
async def test_workflow_low_risk_auto_complete(async_test_db):
    session = async_test_db

    vendor = Vendor(name="LowRiskCorp", domain="lowrisk.com", website_url="https://lowrisk.com")
    session.add(vendor)
    await session.commit()

    mock_emb = MockEmbeddingService()
    vec_store = InMemoryVectorStore()
    runner = create_test_runner("lowrisk.com", "We use cookies for site analytics.", mock_emb, vec_store)

    mock_result = build_mock_assessment_result("lowrisk.com", overall_risk="Low", score=10.0)

    state = await runner.run_workflow(
        db=session,
        vendor_id=vendor.id,
        mock_ai_result=mock_result,
        mock_summary="Executive Summary: LowRiskCorp maintains strong security posture."
    )

    assert state["status"] == "completed"
    assert state["current_step"] == "executive_report"
    assert state["requires_human_approval"] is False
    assert state["overall_score"] < 25.0
    assert state["risk_tier"] == "Low"
    assert "LowRiskCorp" in state["executive_summary"]


# 2. Critical-risk workflow pauses at HITL
@pytest.mark.asyncio
async def test_workflow_critical_risk_hitl_pause(async_test_db):
    session = async_test_db

    vendor = Vendor(name="CritCorp", domain="crit.com", website_url="https://crit.com")
    session.add(vendor)
    await session.commit()

    mock_emb = MockEmbeddingService()
    vec_store = InMemoryVectorStore()
    runner = create_test_runner("crit.com", "We sell personal information to advertising networks. Backups are stored unencrypted.", mock_emb, vec_store)

    mock_result = build_mock_assessment_result("crit.com", overall_risk="Critical", score=100.0)

    state = await runner.run_workflow(
        db=session,
        vendor_id=vendor.id,
        mock_ai_result=mock_result
    )

    assert state["status"] == "awaiting_approval"
    assert state["current_step"] == "human_approval"
    assert state["requires_human_approval"] is True
    assert state["overall_score"] >= 75.0 or state["risk_tier"] == "Critical"
    assert state["human_approved"] is None


# 3. Approval resumes paused workflow
@pytest.mark.asyncio
async def test_workflow_approval_resumption(async_test_db):
    session = async_test_db

    vendor = Vendor(name="CritCorp2", domain="crit2.com", website_url="https://crit2.com")
    session.add(vendor)
    await session.commit()

    mock_emb = MockEmbeddingService()
    vec_store = InMemoryVectorStore()
    runner = create_test_runner("crit2.com", "We sell personal information to advertising networks. Backups are stored unencrypted.", mock_emb, vec_store)

    mock_result = build_mock_assessment_result("crit2.com", overall_risk="Critical", score=100.0)

    state = await runner.run_workflow(db=session, vendor_id=vendor.id, mock_ai_result=mock_result)
    workflow_id = state["workflow_id"]

    assert state["status"] == "awaiting_approval"

    # Submit Approval
    resumed_state = await runner.resume_approval(
        db=session,
        workflow_id=workflow_id,
        approved=True,
        notes="Risk accepted by CISO due to critical business necessity.",
        mock_summary="Executive Summary: Risk accepted after human review."
    )

    assert resumed_state["status"] == "completed"
    assert resumed_state["human_approved"] is True
    assert resumed_state["approval_notes"] == "Risk accepted by CISO due to critical business necessity."
    assert resumed_state["executive_summary"] == "Executive Summary: Risk accepted after human review."


# 4. Rejection terminates workflow
@pytest.mark.asyncio
async def test_workflow_rejection_termination(async_test_db):
    session = async_test_db

    vendor = Vendor(name="RejectCorp", domain="reject.com", website_url="https://reject.com")
    session.add(vendor)
    await session.commit()

    mock_emb = MockEmbeddingService()
    vec_store = InMemoryVectorStore()
    runner = create_test_runner("reject.com", "We sell personal information to advertising networks. Backups are stored unencrypted.", mock_emb, vec_store)

    mock_result = build_mock_assessment_result("reject.com", overall_risk="Critical", score=100.0)

    state = await runner.run_workflow(db=session, vendor_id=vendor.id, mock_ai_result=mock_result)
    workflow_id = state["workflow_id"]

    assert state["status"] == "awaiting_approval"

    # Submit Rejection
    resumed_state = await runner.resume_approval(
        db=session,
        workflow_id=workflow_id,
        approved=False,
        notes="Vendor failed security standards. Procurement rejected."
    )

    assert resumed_state["status"] == "rejected"
    assert resumed_state["human_approved"] is False
    assert resumed_state["approval_notes"] == "Vendor failed security standards. Procurement rejected."


# 5. Security & Vendor Isolation
@pytest.mark.asyncio
async def test_workflow_vendor_isolation(async_test_db):
    session = async_test_db

    v1 = Vendor(name="IsoAlpha", domain="isoalpha.com", website_url="https://isoalpha.com")
    v2 = Vendor(name="IsoBeta", domain="isobeta.com", website_url="https://isobeta.com")
    session.add_all([v1, v2])
    await session.commit()

    mock_emb = MockEmbeddingService()
    vec_store = InMemoryVectorStore()
    runner = create_test_runner("isoalpha.com", "IsoAlpha retains data for 30 days.", mock_emb, vec_store)

    mock_result_alpha = build_mock_assessment_result("isoalpha.com", overall_risk="Low", score=10.0)

    state_alpha = await runner.run_workflow(db=session, vendor_id=v1.id, mock_ai_result=mock_result_alpha)

    # Verify citations in IsoAlpha workflow belong strictly to IsoAlpha
    for cit in state_alpha["citations"]:
        assert "isoalpha.com" in cit["source_url"]
        assert "isobeta.com" not in cit["source_url"]


# 6. Failure Handling
@pytest.mark.asyncio
async def test_workflow_failure_handling(async_test_db):
    session = async_test_db

    runner = VendorRiskWorkflowRunner()
    state = await runner.run_workflow(db=session, vendor_id="invalid-vendor-id")

    assert state["status"] == "failed"
    assert len(state["errors"]) > 0
    assert "not found" in state["errors"][0]


# 7. Persistence Recovery After Backend Restart
@pytest.mark.asyncio
async def test_workflow_recovery_after_backend_restart(async_test_db):
    session = async_test_db

    vendor = Vendor(name="RestartCorp", domain="restart.com", website_url="https://restart.com")
    session.add(vendor)
    await session.commit()

    mock_emb = MockEmbeddingService()
    vec_store = InMemoryVectorStore()
    
    # 1. Start workflow on process 1 (runner1)
    runner1 = create_test_runner("restart.com", "We sell personal information to advertising networks. Backups are stored unencrypted.", mock_emb, vec_store)
    mock_result = build_mock_assessment_result("restart.com", overall_risk="Critical", score=100.0)
    
    state1 = await runner1.run_workflow(db=session, vendor_id=vendor.id, mock_ai_result=mock_result)
    workflow_id = state1["workflow_id"]
    assert state1["status"] == "awaiting_approval"

    # 2. Simulate Backend Process Restart (create fresh runner2 instance with shared checkpointer)
    saver = await runner1._get_saver()
    runner2 = create_test_runner("restart.com", "We sell personal information to advertising networks. Backups are stored unencrypted.", mock_emb, vec_store)
    runner2._checkpointer = saver  # share persistent store instance

    # 3. Retrieve state on new process
    recovered_state = await runner2.get_workflow_state(workflow_id)
    assert recovered_state is not None
    assert recovered_state["workflow_id"] == workflow_id
    assert recovered_state["status"] == "awaiting_approval"
    assert recovered_state["requires_human_approval"] is True

    # 4. Resume approval on runner2
    resumed_state = await runner2.resume_approval(
        db=session,
        workflow_id=workflow_id,
        approved=True,
        notes="Approved on runner2 after backend restart.",
        mock_summary="Executive Summary: Restored & Approved."
    )

    assert resumed_state["status"] == "completed"
    assert resumed_state["human_approved"] is True
    assert resumed_state["approval_notes"] == "Approved on runner2 after backend restart."


# 8. Agentic API Endpoints
@pytest.mark.asyncio
async def test_agentic_api_endpoints(async_test_db):
    session = async_test_db

    vendor = Vendor(name="APICorp", domain="apicorp.com", website_url="https://apicorp.com")
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.api.v1.endpoints.agentic.get_workflow_runner") as MockRunnerGetter:
        mock_runner = MagicMock()
        
        # Mock run_workflow
        mock_runner.run_workflow = AsyncMock(return_value={
            "workflow_id": "wf-123",
            "vendor_id": vendor.id,
            "vendor_name": vendor.name,
            "domain": vendor.domain,
            "status": "awaiting_approval",
            "current_step": "human_approval",
            "overall_score": 85.0,
            "risk_tier": "Critical",
            "requires_human_approval": True,
            "human_approved": None,
            "approval_notes": None,
            "executive_summary": "",
            "indexed_chunks_count": 5,
            "errors": []
        })

        # Mock get_workflow_state
        mock_runner.get_workflow_state = AsyncMock(return_value={
            "workflow_id": "wf-123",
            "vendor_id": vendor.id,
            "vendor_name": vendor.name,
            "domain": vendor.domain,
            "status": "awaiting_approval",
            "current_step": "human_approval",
            "overall_score": 85.0,
            "risk_tier": "Critical",
            "requires_human_approval": True,
            "human_approved": None,
            "approval_notes": None,
            "executive_summary": "",
            "indexed_chunks_count": 5,
            "errors": []
        })

        # Mock resume_approval
        mock_runner.resume_approval = AsyncMock(return_value={
            "workflow_id": "wf-123",
            "vendor_id": vendor.id,
            "vendor_name": vendor.name,
            "domain": vendor.domain,
            "status": "completed",
            "current_step": "executive_report",
            "overall_score": 85.0,
            "risk_tier": "Critical",
            "requires_human_approval": True,
            "human_approved": True,
            "approval_notes": "Approved by CISO",
            "executive_summary": "Executive Summary: Approved.",
            "indexed_chunks_count": 5,
            "errors": []
        })

        MockRunnerGetter.return_value = mock_runner
        client = TestClient(app)

        # 1. POST /api/v1/agentic/workflow/run
        run_res = client.post("/api/v1/agentic/workflow/run", json={"vendor_id": vendor.id})
        assert run_res.status_code == 200
        run_data = run_res.json()
        assert run_data["workflow_id"] == "wf-123"
        assert run_data["status"] == "awaiting_approval"
        assert run_data["requires_human_approval"] is True

        # 2. GET /api/v1/agentic/workflow/status/{workflow_id}
        status_res = client.get("/api/v1/agentic/workflow/status/wf-123")
        assert status_res.status_code == 200
        status_data = status_res.json()
        assert status_data["workflow_id"] == "wf-123"

        # 3. POST /api/v1/agentic/workflow/approve/{workflow_id}
        app_res = client.post("/api/v1/agentic/workflow/approve/wf-123", json={"approved": True, "notes": "Approved by CISO"})
        assert app_res.status_code == 200
        app_data = app_res.json()
        assert app_data["status"] == "completed"
        assert app_data["human_approved"] is True

    app.dependency_overrides.clear()
