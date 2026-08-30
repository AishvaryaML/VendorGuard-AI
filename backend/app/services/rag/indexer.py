import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.vendor import Vendor
from app.models.document import Document, PolicyVersion
from app.models.document_chunk import DocumentChunk
from app.services.rag.chunker import TextChunker, ChunkData
from app.services.rag.embeddings import BaseEmbeddingService, get_embedding_service
from app.services.rag.vector_store import (
    BaseVectorStore,
    VectorRecord,
    get_vector_store,
)

logger = logging.getLogger("vendorguard.rag.indexer")


class RAGIndexer:
    """
    RAG Policy Document Indexer Service.
    Transforms raw PolicyVersions into chunked, embedded vector records while maintaining strict DB traceability.
    Handles duplicate prevention and clean re-indexing.
    """

    def __init__(
        self,
        chunker: Optional[TextChunker] = None,
        embedding_service: Optional[BaseEmbeddingService] = None,
        vector_store: Optional[BaseVectorStore] = None,
    ):
        self.chunker = chunker or TextChunker()
        self.embedding_service = embedding_service or get_embedding_service()
        self.vector_store = vector_store or get_vector_store()

    async def index_policy_version(
        self,
        db: AsyncSession,
        policy_version_id: str,
        force_reindex: bool = False
    ) -> Dict[str, Any]:
        """
        Indexes a specific PolicyVersion:
        1. Loads PolicyVersion + Document + Vendor.
        2. Checks if already indexed to prevent duplicate processing.
        3. Cleans up old chunks/vectors if force_reindex=True.
        4. Chunks text, generates embeddings, persists DocumentChunk DB records, and stores vectors.
        """
        stmt = (
            select(PolicyVersion)
            .options(
                selectinload(PolicyVersion.document).selectinload(Document.vendor),
                selectinload(PolicyVersion.chunks)
            )
            .where(PolicyVersion.id == policy_version_id)
        )
        res = await db.execute(stmt)
        pv = res.scalar_one_or_none()

        if not pv:
            raise ValueError(f"PolicyVersion with ID '{policy_version_id}' not found.")

        document = pv.document
        vendor = document.vendor

        # Check existing indexed chunks in DB
        existing_chunks_stmt = select(DocumentChunk).where(
            DocumentChunk.policy_version_id == policy_version_id
        )
        existing_res = await db.execute(existing_chunks_stmt)
        existing_chunks = list(existing_res.scalars().all())

        vec_count = await self.vector_store.count(policy_version_id=policy_version_id)

        if existing_chunks and vec_count > 0 and not force_reindex:
            logger.info(
                f"PolicyVersion '{policy_version_id}' already indexed ({len(existing_chunks)} chunks). Skipping."
            )
            return {
                "status": "already_indexed",
                "policy_version_id": policy_version_id,
                "chunks_count": len(existing_chunks),
                "reindexed": False
            }

        # Clear existing DB chunks and vectors if re-indexing
        if existing_chunks or vec_count > 0:
            await db.execute(
                delete(DocumentChunk).where(DocumentChunk.policy_version_id == policy_version_id)
            )
            await db.commit()
            await self.vector_store.delete_records(policy_version_id=policy_version_id)

        # 1. Chunk document raw text
        chunk_data_list: List[ChunkData] = self.chunker.chunk_text(
            text=pv.raw_content,
            policy_version_id=pv.id
        )

        if not chunk_data_list:
            logger.warning(f"PolicyVersion '{policy_version_id}' has empty text or no chunks generated.")
            return {
                "status": "empty",
                "policy_version_id": policy_version_id,
                "chunks_count": 0,
                "reindexed": force_reindex
            }

        # 2. Generate embeddings in batch
        texts_to_embed = [c.text for c in chunk_data_list]
        embeddings = await self.embedding_service.embed_documents(texts_to_embed)

        # Update vector store fingerprint and clear if provider/model switched
        model_name = getattr(self.embedding_service, "model_name", "default")
        self.vector_store.check_and_update_fingerprint(
            provider=settings.AI_PROVIDER,
            model=model_name,
            dimension=self.embedding_service.dimension
        )

        # 3. Create DocumentChunk DB records & VectorRecords
        db_chunks: List[DocumentChunk] = []
        vector_records: List[VectorRecord] = []

        for chunk_data, emb in zip(chunk_data_list, embeddings):
            db_chunk = DocumentChunk(
                id=chunk_data.chunk_id,
                vendor_id=vendor.id,
                document_id=document.id,
                policy_version_id=pv.id,
                chunk_index=chunk_data.chunk_index,
                text=chunk_data.text,
                content_hash=chunk_data.content_hash,
                token_count=chunk_data.token_count
            )
            db_chunks.append(db_chunk)

            vec_rec = VectorRecord(
                chunk_id=chunk_data.chunk_id,
                vendor_id=vendor.id,
                document_id=document.id,
                policy_version_id=pv.id,
                document_type=document.document_type,
                vendor_name=vendor.name,
                source_url=document.url,
                chunk_index=chunk_data.chunk_index,
                text=chunk_data.text,
                content_hash=chunk_data.content_hash,
                embedding=emb,
                metadata={
                    "document_title": document.title,
                    "version_number": pv.version_number,
                }
            )
            vector_records.append(vec_rec)

        # Persist DB records
        db.add_all(db_chunks)
        await db.commit()

        # Add to Vector Store
        await self.vector_store.add_records(vector_records)

        logger.info(
            f"Successfully indexed PolicyVersion '{policy_version_id}' ({len(db_chunks)} chunks)."
        )

        return {
            "status": "indexed",
            "policy_version_id": policy_version_id,
            "vendor_id": vendor.id,
            "document_id": document.id,
            "chunks_count": len(db_chunks),
            "reindexed": force_reindex
        }

    async def index_document(
        self,
        db: AsyncSession,
        document_id: str,
        force_reindex: bool = False
    ) -> List[Dict[str, Any]]:
        """Indexes latest PolicyVersion for a Document."""
        stmt = (
            select(Document)
            .options(selectinload(Document.versions))
            .where(Document.id == document_id)
        )
        res = await db.execute(stmt)
        document = res.scalar_one_or_none()

        if not document:
            raise ValueError(f"Document with ID '{document_id}' not found.")

        if not document.versions:
            logger.warning(f"Document '{document_id}' has no PolicyVersions to index.")
            return []

        # Index latest version (versions ordered by version_number desc)
        latest_version = document.versions[0]
        result = await self.index_policy_version(db, latest_version.id, force_reindex=force_reindex)
        return [result]

    async def index_vendor_documents(
        self,
        db: AsyncSession,
        vendor_id: str,
        force_reindex: bool = False
    ) -> List[Dict[str, Any]]:
        """Indexes all documents/latest versions for a Vendor."""
        stmt = (
            select(Vendor)
            .options(selectinload(Vendor.documents).selectinload(Document.versions))
            .where(Vendor.id == vendor_id)
        )
        res = await db.execute(stmt)
        vendor = res.scalar_one_or_none()

        if not vendor:
            raise ValueError(f"Vendor with ID '{vendor_id}' not found.")

        results = []
        for doc in vendor.documents:
            if doc.versions:
                latest_version = doc.versions[0]
                res_info = await self.index_policy_version(db, latest_version.id, force_reindex=force_reindex)
                results.append(res_info)

        return results
