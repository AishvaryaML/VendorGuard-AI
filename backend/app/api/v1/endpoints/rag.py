from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.rag import (
    RAGIndexRequest,
    RAGIndexResponse,
    RAGSearchRequest,
    RAGSearchResponse,
    RAGSearchResultItem,
)
from app.services.rag import RAGIndexer, RAGRetriever
from app.services.vendor_service import get_vendor_by_id

router = APIRouter()


@router.post("/index/{vendor_id}", response_model=RAGIndexResponse, status_code=status.HTTP_200_OK)
async def index_vendor(
    vendor_id: str,
    payload: Optional[RAGIndexRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Development & verification endpoint to manually trigger RAG document chunking and vector indexing for a vendor.
    """
    vendor = await get_vendor_by_id(db=db, vendor_id=vendor_id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID '{vendor_id}' not found."
        )

    force_reindex = payload.force_reindex if payload else False

    try:
        indexer = RAGIndexer()
        results = await indexer.index_vendor_documents(db=db, vendor_id=vendor_id, force_reindex=force_reindex)
        
        total_chunks = sum(item.get("chunks_count", 0) for item in results)
        
        return RAGIndexResponse(
            vendor_id=vendor_id,
            documents_indexed=len(results),
            total_chunks=total_chunks,
            details=results
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG indexing failed for vendor '{vendor.name}': {str(exc)}"
        )


@router.post("/search", response_model=RAGSearchResponse, status_code=status.HTTP_200_OK)
async def search_rag(
    payload: RAGSearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Development & verification endpoint to execute isolated semantic similarity search against vendor policy chunks.
    """
    vendor = await get_vendor_by_id(db=db, vendor_id=payload.vendor_id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID '{payload.vendor_id}' not found."
        )

    try:
        retriever = RAGRetriever()
        results = await retriever.search(
            vendor_id=payload.vendor_id,
            query=payload.query,
            top_k=payload.top_k,
            document_id=payload.document_id,
            db=db,
            auto_index_if_empty=True
        )

        items = [
            RAGSearchResultItem(
                vendor_id=res.vendor_id,
                vendor_name=res.vendor_name,
                document_id=res.document_id,
                policy_version_id=res.policy_version_id,
                document_type=res.document_type,
                source_url=res.source_url,
                chunk_id=res.chunk_id,
                chunk_index=res.chunk_index,
                content_hash=res.content_hash,
                similarity_score=res.similarity_score,
                text=res.text,
                metadata=res.metadata
            )
            for res in results
        ]

        return RAGSearchResponse(
            vendor_id=payload.vendor_id,
            query=payload.query,
            total_results=len(items),
            results=items
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG search failed: {str(exc)}"
        )
