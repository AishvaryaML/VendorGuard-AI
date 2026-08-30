import logging
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.schemas.assistant import (
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantCitation,
    ChatMessagePayload,
)
from app.services.rag import RAGRetriever, RetrievalResult
from app.services.vendor_service import get_vendor_by_id
from app.services.llm import BaseLLMService, get_llm_service

logger = logging.getLogger("vendorguard.assistant")


class VendorAssistantService:
    """
    RAG-grounded Vendor Assistant service.
    Answers user questions strictly using retrieved vendor policy evidence and formats verified citations.
    Supports pluggable LLM provider abstractions (OpenAI, Ollama, etc.).
    """

    def __init__(
        self,
        retriever: Optional[RAGRetriever] = None,
        llm_service: Optional[BaseLLMService] = None,
        openai_api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self.retriever = retriever or RAGRetriever()
        self.llm_service = llm_service or get_llm_service(api_key=openai_api_key, model_name=model_name)
        self.api_key = openai_api_key or settings.OPENAI_API_KEY
        self.model_name = model_name or settings.LLM_MODEL

    async def _call_llm(
        self,
        vendor_name: str,
        evidence_list: List[RetrievalResult],
        user_message: str,
        conversation_history: Optional[List[ChatMessagePayload]] = None
    ) -> str:
        """Invokes LLM provider with grounded RAG context and system prompt."""
        evidence_blocks = []
        for idx, ev in enumerate(evidence_list, 1):
            doc_title = ev.metadata.get("document_title", ev.document_type)
            evidence_blocks.append(
                f"[EVIDENCE ITEM {idx}]\n"
                f"Document Type: {ev.document_type}\n"
                f"Title: {doc_title}\n"
                f"Source URL: {ev.source_url}\n"
                f"Excerpt: {ev.text}\n"
            )

        evidence_text = "\n".join(evidence_blocks)

        return await self.llm_service.generate_assistant_answer(
            vendor_name=vendor_name,
            evidence_text=evidence_text,
            user_message=user_message,
            conversation_history=conversation_history
        )

    async def chat(
        self,
        db: AsyncSession,
        payload: AssistantChatRequest,
        mock_llm_answer: Optional[str] = None
    ) -> AssistantChatResponse:
        """
        Executes grounded RAG assistant chat:
        1. Validates vendor existence.
        2. Retrieves top-k evidence chunks from RAGRetriever for vendor_id.
        3. Formats evidence and citations.
        4. Calls LLM (or mock) with grounded prompt.
        5. Returns AssistantChatResponse with answer and citations.
        """
        if not payload.message or not payload.message.strip():
            raise ValueError("Message prompt cannot be empty.")

        vendor = await get_vendor_by_id(db=db, vendor_id=payload.vendor_id)
        if not vendor:
            raise ValueError(f"Vendor with ID '{payload.vendor_id}' not found.")

        # 1. Retrieve RAG evidence chunks for vendor
        evidence_results: List[RetrievalResult] = await self.retriever.search(
            vendor_id=payload.vendor_id,
            query=payload.message,
            top_k=settings.RAG_TOP_K,
            db=db,
            auto_index_if_empty=True
        )

        # 2. Build citations list from retrieval results
        citations: List[AssistantCitation] = []
        for ev in evidence_results:
            doc_title = ev.metadata.get("document_title", ev.document_type)
            citations.append(
                AssistantCitation(
                    document_type=ev.document_type,
                    title=doc_title,
                    source_url=ev.source_url,
                    snippet=ev.text,
                    similarity_score=ev.similarity_score,
                    chunk_id=ev.chunk_id,
                )
            )

        # 3. Handle case where no evidence chunks exist at all for vendor
        if not evidence_results:
            insufficient_msg = (
                f"There is insufficient evidence in the indexed policy documents for vendor '{vendor.name}' to answer your request."
            )
            return AssistantChatResponse(
                vendor_id=payload.vendor_id,
                answer=insufficient_msg,
                sources=[],
                timestamp=datetime.now(timezone.utc)
            )

        # 4. Generate grounded LLM response
        if mock_llm_answer is not None:
            answer = mock_llm_answer
        else:
            answer = await self._call_llm(
                vendor_name=vendor.name,
                evidence_list=evidence_results,
                user_message=payload.message,
                conversation_history=payload.conversation_history
            )

        return AssistantChatResponse(
            vendor_id=payload.vendor_id,
            answer=answer,
            sources=citations,
            timestamp=datetime.now(timezone.utc)
        )
