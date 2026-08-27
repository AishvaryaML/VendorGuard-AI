import math
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from app.core.config import settings

logger = logging.getLogger("vendorguard.rag.vector_store")


@dataclass
class VectorRecord:
    chunk_id: str
    vendor_id: str
    document_id: str
    policy_version_id: str
    document_type: str
    vendor_name: str
    source_url: str
    chunk_index: int
    text: str
    content_hash: str
    embedding: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    record: VectorRecord
    similarity_score: float


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Computes cosine similarity between two float vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_v1 = math.sqrt(sum(a * a for a in v1))
    norm_v2 = math.sqrt(sum(b * b for b in v2))

    if norm_v1 == 0.0 or norm_v2 == 0.0:
        return 0.0

    return dot_product / (norm_v1 * norm_v2)


class BaseVectorStore(ABC):
    """Abstract Vector Store Interface allowing pluggable backends (InMemory, Pinecone, pgvector)."""

    @abstractmethod
    async def add_records(self, records: List[VectorRecord]) -> int:
        """Adds vector records to the store."""
        pass

    @abstractmethod
    async def delete_records(
        self,
        vendor_id: Optional[str] = None,
        document_id: Optional[str] = None,
        policy_version_id: Optional[str] = None
    ) -> int:
        """Deletes vector records matching filters."""
        pass

    @abstractmethod
    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        vendor_id: Optional[str] = None,
        document_id: Optional[str] = None,
        policy_version_id: Optional[str] = None
    ) -> List[SearchResult]:
        """Performs vector similarity search with strict vendor filtering."""
        pass

    @abstractmethod
    async def count(
        self,
        vendor_id: Optional[str] = None,
        policy_version_id: Optional[str] = None
    ) -> int:
        """Returns total vector records stored."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clears all records in vector store."""
        pass


class InMemoryVectorStore(BaseVectorStore):
    """
    Lightweight, fast in-memory vector store for development & testing.
    Supports metadata filtering, strict vendor isolation, and cosine similarity.
    """

    def __init__(self):
        self._records: Dict[str, VectorRecord] = {}

    async def add_records(self, records: List[VectorRecord]) -> int:
        added_count = 0
        for rec in records:
            self._records[rec.chunk_id] = rec
            added_count += 1
        return added_count

    async def delete_records(
        self,
        vendor_id: Optional[str] = None,
        document_id: Optional[str] = None,
        policy_version_id: Optional[str] = None
    ) -> int:
        keys_to_delete = []
        for chunk_id, rec in self._records.items():
            match = True
            if vendor_id and rec.vendor_id != vendor_id:
                match = False
            if document_id and rec.document_id != document_id:
                match = False
            if policy_version_id and rec.policy_version_id != policy_version_id:
                match = False

            if match and (vendor_id or document_id or policy_version_id):
                keys_to_delete.append(chunk_id)

        for k in keys_to_delete:
            del self._records[k]

        return len(keys_to_delete)

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        vendor_id: Optional[str] = None,
        document_id: Optional[str] = None,
        policy_version_id: Optional[str] = None
    ) -> List[SearchResult]:
        if not query_embedding:
            return []

        results: List[SearchResult] = []

        for rec in self._records.values():
            # STRICT VENDOR ISOLATION FILTERING
            if vendor_id and rec.vendor_id != vendor_id:
                continue
            if document_id and rec.document_id != document_id:
                continue
            if policy_version_id and rec.policy_version_id != policy_version_id:
                continue

            score = cosine_similarity(query_embedding, rec.embedding)
            results.append(SearchResult(record=rec, similarity_score=score))

        # Sort by similarity score descending
        results.sort(key=lambda r: r.similarity_score, reverse=True)
        return results[:top_k]

    async def count(
        self,
        vendor_id: Optional[str] = None,
        policy_version_id: Optional[str] = None
    ) -> int:
        if not vendor_id and not policy_version_id:
            return len(self._records)

        count = 0
        for rec in self._records.values():
            if vendor_id and rec.vendor_id != vendor_id:
                continue
            if policy_version_id and rec.policy_version_id != policy_version_id:
                continue
            count += 1
        return count

    async def clear(self) -> None:
        self._records.clear()


# Global Singleton Vector Store Instance for the app
_global_vector_store: Optional[BaseVectorStore] = None


def get_vector_store() -> BaseVectorStore:
    global _global_vector_store
    if _global_vector_store is None:
        _global_vector_store = InMemoryVectorStore()
    return _global_vector_store
