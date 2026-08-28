import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rag import RAGIndexer, RAGRetriever, RetrievalResult
from app.services.agents.state import VendorRiskState

logger = logging.getLogger("vendorguard.agents.policy_auditor")


class PolicyAuditorAgent:
    """
    Specialized Policy Auditor Agent responsible for:
    - Indexing discovered vendor policy documents into vector store using RAGIndexer
    - Retrieving vendor-isolated policy evidence across Privacy, Security, Compliance, Legal
    - Identifying missing or insufficient policy evidence
    - Preserving full document traceability (Vendor -> Document -> PolicyVersion -> Chunk)
    """

    def __init__(
        self,
        indexer: Optional[RAGIndexer] = None,
        retriever: Optional[RAGRetriever] = None,
    ):
        self.indexer = indexer or RAGIndexer()
        self.retriever = retriever or RAGRetriever(indexer=self.indexer)

    async def run(self, state: VendorRiskState, db: AsyncSession) -> Dict[str, Any]:
        vendor_id = state.get("vendor_id")
        vendor_name = state.get("vendor_name", vendor_id)
        logger.info(f"PolicyAuditorAgent executing for vendor '{vendor_name}'")

        state["current_step"] = "policy_auditor"
        state["status"] = "indexing"

        try:
            # 1. Index vendor documents
            index_results = await self.indexer.index_vendor_documents(db=db, vendor_id=vendor_id)
            total_indexed_chunks = sum(item.get("chunks_count", 0) for item in index_results)

            # 2. Retrieve key evidence across risk categories using RAGRetriever
            categories = ["Privacy", "Security", "Compliance", "Legal"]
            extracted_citations: List[Dict[str, Any]] = []

            for cat in categories:
                retrieved: List[RetrievalResult] = await self.retriever.search(
                    vendor_id=vendor_id,
                    query=f"Vendor {vendor_name} {cat} policy controls and risk evidence",
                    top_k=3,
                    db=db,
                    auto_index_if_empty=False
                )
                for item in retrieved:
                    extracted_citations.append({
                        "category": cat,
                        "document_type": item.document_type,
                        "title": item.metadata.get("document_title", item.document_type),
                        "source_url": item.source_url,
                        "chunk_id": item.chunk_id,
                        "chunk_index": item.chunk_index,
                        "content_hash": item.content_hash,
                        "similarity_score": item.similarity_score,
                        "snippet": item.text,
                    })

            logger.info(
                f"PolicyAuditorAgent completed: {total_indexed_chunks} chunks indexed, "
                f"{len(extracted_citations)} evidence snippets extracted for '{vendor_name}'"
            )

            return {
                "indexed_chunks_count": total_indexed_chunks,
                "citations": extracted_citations,
                "current_step": "policy_auditor",
                "status": "policy_audit_completed",
            }

        except Exception as exc:
            err_msg = f"PolicyAuditorAgent failed for vendor '{vendor_name}': {str(exc)}"
            logger.error(err_msg, exc_info=True)
            errors = state.get("errors", [])
            errors.append(err_msg)
            return {
                "current_step": "policy_auditor",
                "status": "failed",
                "errors": errors
            }
