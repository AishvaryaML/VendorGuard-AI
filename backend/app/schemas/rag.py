from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class RAGIndexRequest(BaseModel):
    force_reindex: bool = Field(default=False, description="Forces re-indexing of policy versions even if unchanged.")


class RAGIndexResponse(BaseModel):
    vendor_id: str
    documents_indexed: int
    total_chunks: int
    details: List[Dict[str, Any]]


class RAGSearchRequest(BaseModel):
    vendor_id: str = Field(..., description="Target vendor ID for isolated search.")
    query: str = Field(..., description="Natural language semantic search query.")
    top_k: Optional[int] = Field(default=5, ge=1, le=50, description="Max number of candidate evidence chunks.")
    document_id: Optional[str] = Field(default=None, description="Optional document ID to narrow search.")


class RAGSearchResultItem(BaseModel):
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
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RAGSearchResponse(BaseModel):
    vendor_id: str
    query: str
    total_results: int
    results: List[RAGSearchResultItem]
