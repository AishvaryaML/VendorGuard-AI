import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings
from app.models.vendor import Vendor, RiskTier, VendorStatus, MonitoringFrequency
from app.models.document import Document, PolicyVersion
from app.models.document_chunk import DocumentChunk
from app.services.rag.chunker import TextChunker
from app.services.rag.embeddings import BaseEmbeddingService, OpenAIEmbeddingService
from app.services.rag.vector_store import (
    InMemoryVectorStore,
    VectorRecord,
    cosine_similarity,
)
from app.services.rag.indexer import RAGIndexer
from app.services.rag.retriever import RAGRetriever


# Dummy Mock Embedding Service for fast deterministic tests
class MockEmbeddingService(BaseEmbeddingService):
    @property
    def dimension(self) -> int:
        return 8

    async def embed_text(self, text: str):
        res = await self.embed_documents([text])
        return res[0]

    async def embed_documents(self, texts):
        results = []
        for t in texts:
            # Generate deterministic pseudo-embedding based on text hash/length
            val = float(len(t) % 10 + 1) / 10.0
            vec = [val] * 8
            results.append(vec)
        return results


# Set up SQLite async test DB session fixture
@pytest_asyncio.fixture
async def async_test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


# --- CHUNKER TESTS ---

def test_chunker_normal_text():
    text = (
        "VendorGuard AI provides automated vendor risk assessment. "
        "It monitors vendor privacy policies and terms of service continuous updates. "
        "When policy changes occur, notifications are dispatched to risk analysts."
    )
    chunker = TextChunker(chunk_size=15, chunk_overlap=5)
    chunks = chunker.chunk_text(text, policy_version_id="pv-123")

    assert len(chunks) > 0
    assert chunks[0].chunk_index == 0
    assert chunks[0].token_count > 0
    assert len(chunks[0].content_hash) == 64
    assert chunks[0].chunk_id is not None


def test_chunker_overlap():
    text = "Sentence one is here. Sentence two follows it. Sentence three is the last one."
    chunker = TextChunker(chunk_size=10, chunk_overlap=3)
    chunks = chunker.chunk_text(text)

    assert len(chunks) >= 2
    # Verify that words from sentence one/two spill into adjacent chunks as overlap
    assert "Sentence" in chunks[0].text
    assert "Sentence" in chunks[1].text


def test_chunker_empty_text():
    chunker = TextChunker()
    assert chunker.chunk_text("") == []
    assert chunker.chunk_text("   \n\t  ") == []


def test_chunker_ordering_and_hash():
    text = "Paragraph 1 text.\n\nParagraph 2 text.\n\nParagraph 3 text."
    chunker = TextChunker(chunk_size=5, chunk_overlap=1)
    chunks = chunker.chunk_text(text, policy_version_id="pv-order-test")

    indices = [c.chunk_index for c in chunks]
    assert indices == list(range(len(chunks)))

    # Test stability of chunk ID for same inputs
    chunks_again = chunker.chunk_text(text, policy_version_id="pv-order-test")
    assert chunks[0].chunk_id == chunks_again[0].chunk_id
    assert chunks[0].content_hash == chunks_again[0].content_hash


# --- EMBEDDINGS TESTS ---

@pytest.mark.asyncio
async def test_embedding_service_mocked():
    mock_service = MockEmbeddingService()
    emb = await mock_service.embed_text("Privacy Policy clause")

    assert len(emb) == 8
    assert isinstance(emb, list)
    assert isinstance(emb[0], float)


@pytest.mark.asyncio
async def test_embedding_service_openai_error_handling():
    service = OpenAIEmbeddingService(api_key="")
    with pytest.raises(ValueError, match="OpenAI API key is not configured"):
        await service.embed_text("Some text")


# --- VECTOR STORE & VENDOR ISOLATION TESTS ---

@pytest.mark.asyncio
async def test_vector_store_insert_and_vendor_isolation():
    store = InMemoryVectorStore()

    rec_a = VectorRecord(
        chunk_id="chunk-a1",
        vendor_id="vendor-A",
        document_id="doc-a1",
        policy_version_id="pv-a1",
        document_type="Privacy Policy",
        vendor_name="Acme Corp",
        source_url="https://acme.com/privacy",
        chunk_index=0,
        text="Acme privacy policy detailing data retention and GDPR compliance.",
        content_hash="hash-a1",
        embedding=[1.0, 1.0, 0.0, 0.0]
    )

    rec_b = VectorRecord(
        chunk_id="chunk-b1",
        vendor_id="vendor-B",
        document_id="doc-b1",
        policy_version_id="pv-b1",
        document_type="Terms of Service",
        vendor_name="Beta Inc",
        source_url="https://beta.com/terms",
        chunk_index=0,
        text="Beta terms detailing user agreement and billing policy.",
        content_hash="hash-b1",
        embedding=[1.0, 0.9, 0.0, 0.0]
    )

    await store.add_records([rec_a, rec_b])
    assert await store.count() == 2

    # Query vector close to both
    query_emb = [1.0, 1.0, 0.0, 0.0]

    # Search specifically for vendor-A -> Must NOT return rec_b
    results_a = await store.search(query_embedding=query_emb, top_k=10, vendor_id="vendor-A")
    assert len(results_a) == 1
    assert results_a[0].record.vendor_id == "vendor-A"
    assert results_a[0].record.vendor_name == "Acme Corp"

    # Search specifically for vendor-B -> Must NOT return rec_a
    results_b = await store.search(query_embedding=query_emb, top_k=10, vendor_id="vendor-B")
    assert len(results_b) == 1
    assert results_b[0].record.vendor_id == "vendor-B"
    assert results_b[0].record.vendor_name == "Beta Inc"


@pytest.mark.asyncio
async def test_vector_store_delete_records():
    store = InMemoryVectorStore()
    rec = VectorRecord(
        chunk_id="c1",
        vendor_id="v1",
        document_id="d1",
        policy_version_id="pv1",
        document_type="Privacy",
        vendor_name="V1",
        source_url="http://v1.com",
        chunk_index=0,
        text="Text",
        content_hash="h1",
        embedding=[0.5, 0.5]
    )
    await store.add_records([rec])
    assert await store.count(policy_version_id="pv1") == 1

    # Delete policy version records
    deleted = await store.delete_records(policy_version_id="pv1")
    assert deleted == 1
    assert await store.count(policy_version_id="pv1") == 0


# --- INDEXER & RETRIEVER INTEGRATION TESTS ---

@pytest.mark.asyncio
async def test_indexer_and_retriever_flow(async_test_db):
    session = async_test_db

    # 1. Setup Vendor, Document, PolicyVersion in test DB
    vendor = Vendor(
        name="Test Security Vendor",
        domain="securityvendor.com",
        website_url="https://securityvendor.com",
        risk_tier=RiskTier.LOW,
        current_risk_score=15.0,
        status=VendorStatus.ACTIVE,
        monitoring_frequency=MonitoringFrequency.DAILY
    )
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    doc = Document(
        vendor_id=vendor.id,
        document_type="Security Center",
        title="Vendor Security Whitepaper",
        url="https://securityvendor.com/security",
        current_version_hash="hash-123"
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)

    pv = PolicyVersion(
        document_id=doc.id,
        version_number=1,
        content_hash="hash-123",
        raw_content=(
            "Security Center Overview. All user data is encrypted at rest using AES-256 encryption. "
            "Data in transit is encrypted using TLS 1.3 protocol. "
            "Annual SOC 2 Type II audit reports are available upon request."
        )
    )
    session.add(pv)
    await session.commit()
    await session.refresh(pv)

    # 2. Setup Indexer with MockEmbeddingService and InMemoryVectorStore
    mock_emb = MockEmbeddingService()
    vec_store = InMemoryVectorStore()
    indexer = RAGIndexer(
        chunker=TextChunker(chunk_size=20, chunk_overlap=5),
        embedding_service=mock_emb,
        vector_store=vec_store
    )

    # Index policy version
    index_res = await indexer.index_policy_version(session, pv.id)
    assert index_res["status"] == "indexed"
    assert index_res["chunks_count"] > 0

    # Test duplicate indexing prevention (should skip)
    dup_res = await indexer.index_policy_version(session, pv.id, force_reindex=False)
    assert dup_res["status"] == "already_indexed"
    assert dup_res["reindexed"] is False

    # Test force re-indexing (should re-index cleanly without accumulating duplicate DB chunks)
    reindex_res = await indexer.index_policy_version(session, pv.id, force_reindex=True)
    assert reindex_res["status"] == "indexed"
    assert reindex_res["reindexed"] is True

    # Check DB DocumentChunks count for policy_version
    stmt_chunks = select(DocumentChunk).where(DocumentChunk.policy_version_id == pv.id)
    chunks_res = await session.execute(stmt_chunks)
    db_chunks = list(chunks_res.scalars().all())
    assert len(db_chunks) == index_res["chunks_count"]

    # 3. Test Retriever with Vendor Isolation and Traceability
    retriever = RAGRetriever(
        embedding_service=mock_emb,
        vector_store=vec_store,
        indexer=indexer
    )

    results = await retriever.search(
        vendor_id=vendor.id,
        query="encryption AES-256",
        top_k=5,
        db=session
    )

    assert len(results) > 0
    res0 = results[0]

    # Verify full document traceability fields
    assert res0.vendor_id == vendor.id
    assert res0.vendor_name == "Test Security Vendor"
    assert res0.document_id == doc.id
    assert res0.policy_version_id == pv.id
    assert res0.document_type == "Security Center"
    assert res0.source_url == "https://securityvendor.com/security"
    assert res0.chunk_id is not None
    assert res0.chunk_index == 0
    assert res0.content_hash is not None
    assert isinstance(res0.similarity_score, float)
    assert "encrypted" in res0.text.lower() or "security" in res0.text.lower()


@pytest.mark.asyncio
async def test_retriever_strict_cross_vendor_isolation(async_test_db):
    session = async_test_db

    # Create Vendor 1
    v1 = Vendor(name="Vendor One", domain="v1.com", website_url="https://v1.com")
    session.add(v1)
    await session.commit()

    d1 = Document(vendor_id=v1.id, document_type="Privacy Policy", title="P1", url="https://v1.com/privacy")
    session.add(d1)
    await session.commit()

    pv1 = PolicyVersion(document_id=d1.id, version_number=1, content_hash="h1", raw_content="Confidential Vendor 1 data breach policy.")
    session.add(pv1)
    await session.commit()

    # Create Vendor 2
    v2 = Vendor(name="Vendor Two", domain="v2.com", website_url="https://v2.com")
    session.add(v2)
    await session.commit()

    d2 = Document(vendor_id=v2.id, document_type="Privacy Policy", title="P2", url="https://v2.com/privacy")
    session.add(d2)
    await session.commit()

    pv2 = PolicyVersion(document_id=d2.id, version_number=1, content_hash="h2", raw_content="Confidential Vendor 2 data breach policy.")
    session.add(pv2)
    await session.commit()

    mock_emb = MockEmbeddingService()
    vec_store = InMemoryVectorStore()
    indexer = RAGIndexer(embedding_service=mock_emb, vector_store=vec_store)

    await indexer.index_policy_version(session, pv1.id)
    await indexer.index_policy_version(session, pv2.id)

    retriever = RAGRetriever(embedding_service=mock_emb, vector_store=vec_store, indexer=indexer)

    # Query for Vendor 1 -> MUST NOT return any chunks from Vendor 2
    results_v1 = await retriever.search(vendor_id=v1.id, query="data breach policy", db=session)
    for r in results_v1:
        assert r.vendor_id == v1.id
        assert r.vendor_id != v2.id

    # Query for Vendor 2 -> MUST NOT return any chunks from Vendor 1
    results_v2 = await retriever.search(vendor_id=v2.id, query="data breach policy", db=session)
    for r in results_v2:
        assert r.vendor_id == v2.id
        assert r.vendor_id != v1.id


# --- RAG API ENDPOINT TESTS ---

@pytest.mark.asyncio
async def test_rag_api_endpoints(async_test_db):
    session = async_test_db

    # Create dummy vendor and document in test session
    vendor = Vendor(name="API Vendor", domain="apivendor.com", website_url="https://apivendor.com")
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    doc = Document(vendor_id=vendor.id, document_type="Privacy Policy", title="Privacy", url="https://apivendor.com/privacy")
    session.add(doc)
    await session.commit()
    await session.refresh(doc)

    pv = PolicyVersion(document_id=doc.id, version_number=1, content_hash="h-api", raw_content="API Vendor privacy data retention for 30 days.")
    session.add(pv)
    await session.commit()

    # Override get_db dependency for test client
    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.api.v1.endpoints.rag.RAGIndexer") as MockIndexerClass, \
         patch("app.api.v1.endpoints.rag.RAGRetriever") as MockRetrieverClass:
        
        mock_indexer_inst = MagicMock()
        mock_indexer_inst.index_vendor_documents = AsyncMock(return_value=[
            {"status": "indexed", "chunks_count": 2, "policy_version_id": pv.id}
        ])
        MockIndexerClass.return_value = mock_indexer_inst

        mock_retriever_inst = MagicMock()
        mock_retriever_inst.search = AsyncMock(return_value=[
            MagicMock(
                vendor_id=vendor.id,
                vendor_name="API Vendor",
                document_id=doc.id,
                policy_version_id=pv.id,
                document_type="Privacy Policy",
                source_url="https://apivendor.com/privacy",
                chunk_id="c-1",
                chunk_index=0,
                content_hash="h-api",
                similarity_score=0.95,
                text="API Vendor privacy data retention for 30 days.",
                metadata={}
            )
        ])
        MockRetrieverClass.return_value = mock_retriever_inst

        client = TestClient(app)

        # Test POST /api/v1/rag/index/{vendor_id}
        idx_res = client.post(f"/api/v1/rag/index/{vendor.id}", json={"force_reindex": False})
        assert idx_res.status_code == 200
        data = idx_res.json()
        assert data["vendor_id"] == vendor.id
        assert data["total_chunks"] == 2

        # Test POST /api/v1/rag/search
        search_res = client.post("/api/v1/rag/search", json={
            "vendor_id": vendor.id,
            "query": "data retention period",
            "top_k": 3
        })
        assert search_res.status_code == 200
        search_data = search_res.json()
        assert search_data["vendor_id"] == vendor.id
        assert search_data["total_results"] == 1
        assert search_data["results"][0]["text"] == "API Vendor privacy data retention for 30 days."

    app.dependency_overrides.clear()
