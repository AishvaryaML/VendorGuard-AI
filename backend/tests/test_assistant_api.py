import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import Base, get_db
from app.models.vendor import Vendor
from app.models.document import Document, PolicyVersion
from app.schemas.assistant import AssistantChatRequest, ChatMessagePayload
from app.services.assistant_service import VendorAssistantService
from app.services.rag.embeddings import BaseEmbeddingService
from app.services.rag.vector_store import InMemoryVectorStore, VectorRecord
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


# 1. Successful Assistant Chat
@pytest.mark.asyncio
async def test_assistant_chat_success(async_test_db):
    session = async_test_db

    vendor = Vendor(name="CloudCorp", domain="cloudcorp.com", website_url="https://cloudcorp.com")
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    doc = Document(vendor_id=vendor.id, document_type="Privacy Policy", title="CloudCorp Privacy", url="https://cloudcorp.com/privacy")
    session.add(doc)
    await session.commit()
    await session.refresh(doc)

    pv = PolicyVersion(document_id=doc.id, version_number=1, content_hash="h123", raw_content="CloudCorp encrypts all customer data at rest with AES-256.")
    session.add(pv)
    await session.commit()

    mock_emb = MockEmbeddingService()
    vec_store = InMemoryVectorStore()
    indexer = RAGIndexer(embedding_service=mock_emb, vector_store=vec_store)
    await indexer.index_policy_version(session, pv.id)

    retriever = RAGRetriever(embedding_service=mock_emb, vector_store=vec_store, indexer=indexer)
    assistant_service = VendorAssistantService(retriever=retriever)

    req = AssistantChatRequest(vendor_id=vendor.id, message="How is data encrypted at rest?")
    res = await assistant_service.chat(
        db=session,
        payload=req,
        mock_llm_answer="CloudCorp encrypts customer data at rest using AES-256 encryption."
    )

    assert res.vendor_id == vendor.id
    assert "AES-256" in res.answer
    assert len(res.sources) > 0
    assert res.sources[0].source_url == "https://cloudcorp.com/privacy"


# 2. Vendor Not Found
@pytest.mark.asyncio
async def test_assistant_vendor_not_found(async_test_db):
    session = async_test_db
    assistant_service = VendorAssistantService()
    req = AssistantChatRequest(vendor_id="non-existent-vendor-id", message="Tell me about security")

    with pytest.raises(ValueError, match="Vendor with ID 'non-existent-vendor-id' not found"):
        await assistant_service.chat(db=session, payload=req)


# 3. Retrieved Citations are Returned
@pytest.mark.asyncio
async def test_assistant_retrieved_citations_returned(async_test_db):
    session = async_test_db

    vendor = Vendor(name="SecureCo", domain="secureco.com", website_url="https://secureco.com")
    session.add(vendor)
    await session.commit()

    doc = Document(vendor_id=vendor.id, document_type="Security Center", title="SOC 2 Report", url="https://secureco.com/soc2")
    session.add(doc)
    await session.commit()

    pv = PolicyVersion(document_id=doc.id, version_number=1, content_hash="h-soc2", raw_content="SOC 2 Type II audit completed annually by independent CPA firm.")
    session.add(pv)
    await session.commit()

    mock_emb = MockEmbeddingService()
    vec_store = InMemoryVectorStore()
    indexer = RAGIndexer(embedding_service=mock_emb, vector_store=vec_store)
    await indexer.index_policy_version(session, pv.id)

    retriever = RAGRetriever(embedding_service=mock_emb, vector_store=vec_store, indexer=indexer)
    assistant_service = VendorAssistantService(retriever=retriever)

    req = AssistantChatRequest(vendor_id=vendor.id, message="Do you have SOC 2 certification?")
    res = await assistant_service.chat(db=session, payload=req, mock_llm_answer="Yes, SOC 2 Type II audit is completed annually.")

    assert len(res.sources) == 1
    citation = res.sources[0]
    assert citation.document_type == "Security Center"
    assert citation.title == "SOC 2 Report"
    assert citation.source_url == "https://secureco.com/soc2"
    assert "SOC 2 Type II" in citation.snippet
    assert isinstance(citation.similarity_score, float)
    assert citation.chunk_id is not None


# 4. Vendor Isolation
@pytest.mark.asyncio
async def test_assistant_vendor_isolation(async_test_db):
    session = async_test_db

    v1 = Vendor(name="Vendor Alpha", domain="alpha.com", website_url="https://alpha.com")
    v2 = Vendor(name="Vendor Beta", domain="beta.com", website_url="https://beta.com")
    session.add_all([v1, v2])
    await session.commit()

    d1 = Document(vendor_id=v1.id, document_type="Privacy", title="Alpha Privacy", url="https://alpha.com/p")
    d2 = Document(vendor_id=v2.id, document_type="Privacy", title="Beta Privacy", url="https://beta.com/p")
    session.add_all([d1, d2])
    await session.commit()

    pv1 = PolicyVersion(document_id=d1.id, version_number=1, content_hash="ha", raw_content="Alpha retains data for 90 days.")
    pv2 = PolicyVersion(document_id=d2.id, version_number=1, content_hash="hb", raw_content="Beta retains data for 10 years.")
    session.add_all([pv1, pv2])
    await session.commit()

    mock_emb = MockEmbeddingService()
    vec_store = InMemoryVectorStore()
    indexer = RAGIndexer(embedding_service=mock_emb, vector_store=vec_store)
    await indexer.index_policy_version(session, pv1.id)
    await indexer.index_policy_version(session, pv2.id)

    retriever = RAGRetriever(embedding_service=mock_emb, vector_store=vec_store, indexer=indexer)
    assistant_service = VendorAssistantService(retriever=retriever)

    # Query Alpha -> must NOT return Beta citations
    req_alpha = AssistantChatRequest(vendor_id=v1.id, message="What is data retention?")
    res_alpha = await assistant_service.chat(db=session, payload=req_alpha, mock_llm_answer="Alpha retains data for 90 days.")

    for source in res_alpha.sources:
        assert source.source_url == "https://alpha.com/p"
        assert source.source_url != "https://beta.com/p"


# 5. Insufficient Evidence Behavior
@pytest.mark.asyncio
async def test_assistant_insufficient_evidence(async_test_db):
    session = async_test_db

    vendor = Vendor(name="EmptyVendor", domain="empty.com", website_url="https://empty.com")
    session.add(vendor)
    await session.commit()

    # Vendor has no documents at all
    retriever = RAGRetriever(embedding_service=MockEmbeddingService(), vector_store=InMemoryVectorStore())
    assistant_service = VendorAssistantService(retriever=retriever)

    req = AssistantChatRequest(vendor_id=vendor.id, message="What is your SOC 2 status?")
    res = await assistant_service.chat(db=session, payload=req)

    assert "insufficient evidence" in res.answer.lower()
    assert res.sources == []


# 6. Conversation History Accepted
@pytest.mark.asyncio
async def test_assistant_conversation_history_accepted(async_test_db):
    session = async_test_db

    vendor = Vendor(name="HistCorp", domain="hist.com", website_url="https://hist.com")
    session.add(vendor)
    await session.commit()

    doc = Document(vendor_id=vendor.id, document_type="Terms", title="TOS", url="https://hist.com/terms")
    session.add(doc)
    await session.commit()

    pv = PolicyVersion(document_id=doc.id, version_number=1, content_hash="ht", raw_content="HistCorp offers SLA uptime guarantee of 99.9%.")
    session.add(pv)
    await session.commit()

    mock_emb = MockEmbeddingService()
    vec_store = InMemoryVectorStore()
    indexer = RAGIndexer(embedding_service=mock_emb, vector_store=vec_store)
    await indexer.index_policy_version(session, pv.id)

    retriever = RAGRetriever(embedding_service=mock_emb, vector_store=vec_store, indexer=indexer)
    assistant_service = VendorAssistantService(retriever=retriever)

    history = [
        ChatMessagePayload(role="user", content="Hi, do you have SLAs?"),
        ChatMessagePayload(role="assistant", content="Yes, HistCorp provides SLAs.")
    ]

    req = AssistantChatRequest(vendor_id=vendor.id, message="What is the exact percentage?", conversation_history=history)
    res = await assistant_service.chat(db=session, payload=req, mock_llm_answer="The exact SLA uptime guarantee is 99.9%.")

    assert "99.9%" in res.answer


# 7. LLM Failure Handling
@pytest.mark.asyncio
async def test_assistant_llm_failure_handling(async_test_db):
    session = async_test_db

    vendor = Vendor(name="FailCorp", domain="fail.com", website_url="https://fail.com")
    session.add(vendor)
    await session.commit()

    doc = Document(vendor_id=vendor.id, document_type="Privacy", title="P", url="https://fail.com/p")
    session.add(doc)
    await session.commit()

    pv = PolicyVersion(document_id=doc.id, version_number=1, content_hash="hf", raw_content="FailCorp text.")
    session.add(pv)
    await session.commit()

    mock_emb = MockEmbeddingService()
    vec_store = InMemoryVectorStore()
    indexer = RAGIndexer(embedding_service=mock_emb, vector_store=vec_store)
    await indexer.index_policy_version(session, pv.id)

    retriever = RAGRetriever(embedding_service=mock_emb, vector_store=vec_store, indexer=indexer)
    
    # Assistant initialized with empty API key to trigger error on _call_llm
    assistant_service = VendorAssistantService(retriever=retriever, openai_api_key="")

    req = AssistantChatRequest(vendor_id=vendor.id, message="What is FailCorp?")
    with pytest.raises(ValueError, match="OpenAI API key is not configured"):
        await assistant_service.chat(db=session, payload=req)


# 8. Empty/Invalid Message Handling
@pytest.mark.asyncio
async def test_assistant_empty_message_handling(async_test_db):
    session = async_test_db

    vendor = Vendor(name="Vendor", domain="v.com", website_url="https://v.com")
    session.add(vendor)
    await session.commit()

    assistant_service = VendorAssistantService()

    req = AssistantChatRequest(vendor_id=vendor.id, message="   ")
    with pytest.raises(ValueError, match="Message prompt cannot be empty"):
        await assistant_service.chat(db=session, payload=req)


# 9. API Endpoint Integration Test
@pytest.mark.asyncio
async def test_assistant_api_endpoint(async_test_db):
    session = async_test_db

    vendor = Vendor(name="APIVendor", domain="apiv.com", website_url="https://apiv.com")
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.api.v1.endpoints.assistant.VendorAssistantService") as MockServiceClass:
        mock_svc_inst = MagicMock()
        mock_svc_inst.chat = AsyncMock(return_value={
            "vendor_id": vendor.id,
            "answer": "APIVendor complies with ISO 27001 standard.",
            "sources": [
                {
                    "document_type": "Compliance Doc",
                    "title": "ISO Cert",
                    "source_url": "https://apiv.com/iso",
                    "snippet": "APIVendor is ISO 27001 certified.",
                    "similarity_score": 0.92,
                    "chunk_id": "c-iso-1"
                }
            ],
            "timestamp": "2026-08-27T23:00:00Z"
        })
        MockServiceClass.return_value = mock_svc_inst

        client = TestClient(app)

        res = client.post("/api/v1/assistant/chat", json={
            "vendor_id": vendor.id,
            "message": "Is APIVendor ISO 27001 certified?"
        })

        assert res.status_code == 200
        data = res.json()
        assert data["vendor_id"] == vendor.id
        assert "ISO 27001" in data["answer"]
        assert len(data["sources"]) == 1
        assert data["sources"][0]["source_url"] == "https://apiv.com/iso"

    app.dependency_overrides.clear()
