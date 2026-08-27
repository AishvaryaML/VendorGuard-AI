import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.rag.embeddings import BaseEmbeddingService, OpenAIEmbeddingService
from app.services.rag.vector_store import (
    BaseVectorStore,
    SearchResult,
    get_vector_store,
)
from app.services.rag.indexer import RAGIndexer

logger = logging.getLogger("vendorguard.rag.retriever")


@dataclass
class RetrievalResult:
    vendor_id: str
    vendor_name: str
    document_id: str
    policy_version_id: str
    document_type: str
    source_url: str
    chunk_id: str
    chunk_index: int
    content_hash: str
    similarity_score: float
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class RAGRetriever:
    """
    RAG Retrieval Service enforcing strict vendor isolation, query embedding, and rich evidence metadata.
    """

    def __init__(
        self,
        embedding_service: Optional[BaseEmbeddingService] = None,
        vector_store: Optional[BaseVectorStore] = None,
        indexer: Optional[RAGIndexer] = None,
    ):
        self.embedding_service = embedding_service or OpenAIEmbeddingService()
        self.vector_store = vector_store or get_vector_store()
        self.indexer = indexer or RAGIndexer(
            embedding_service=self.embedding_service,
            vector_store=self.vector_store,
        )

    async def search(
        self,
        vendor_id: str,
        query: str,
        top_k: Optional[int] = None,
        document_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        auto_index_if_empty: bool = True
    ) -> List[RetrievalResult]:
        """
        Executes semantic RAG similarity search for a natural language query:
        1. Validates non-empty query and vendor_id.
        2. Auto-indexes vendor documents if vector store contains 0 vectors for this vendor.
        3. Embeds query string into vector embedding.
        4. Queries vector store with STRICT vendor isolation filter (rec.vendor_id == vendor_id).
        5. Formats results into structured RetrievalResult evidence records.
        """
        if not vendor_id or not vendor_id.strip():
            raise ValueError("vendor_id is required for RAG search to enforce vendor isolation.")

        if not query or not query.strip():
            return []

        k = top_k or settings.RAG_TOP_K

        # Auto-index vendor documents if zero vectors found for vendor
        if auto_index_if_empty and db is not None:
            vec_count = await self.vector_store.count(vendor_id=vendor_id)
            if vec_count == 0:
                logger.info(f"Vector store empty for vendor '{vendor_id}'. Triggering auto-indexing.")
                await self.indexer.index_vendor_documents(db=db, vendor_id=vendor_id)

        # Generate embedding for search query
        query_embedding = await self.embedding_service.embed_text(query)

        # Search vector store with vendor isolation
        search_results: List[SearchResult] = await self.vector_store.search(
            query_embedding=query_embedding,
            top_k=k,
            vendor_id=vendor_id,
            document_id=document_id
        )

        retrieved: List[RetrievalResult] = []
        for res in search_results:
            rec = res.record
            retrieved.append(
                RetrievalResult(
                    vendor_id=rec.vendor_id,
                    vendor_name=rec.vendor_name,
                    document_id=rec.document_id,
                    policy_version_id=rec.policy_version_id,
                    document_type=rec.document_type,
                    source_url=rec.source_url,
                    chunk_id=rec.chunk_id,
                    chunk_index=rec.chunk_index,
                    content_hash=rec.content_hash,
                    similarity_score=round(res.similarity_score, 4),
                    text=rec.text,
                    metadata=rec.metadata,
                )
            )

        return retrieved
