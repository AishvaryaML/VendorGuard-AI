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

logger = logging.getLogger("vendorguard.assistant")


class VendorAssistantService:
    """
    RAG-grounded Vendor Assistant service.
    Answers user questions strictly using retrieved vendor policy evidence and formats verified citations.
    """

    def __init__(
        self,
        retriever: Optional[RAGRetriever] = None,
        openai_api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self.retriever = retriever or RAGRetriever()
        self.api_key = openai_api_key or settings.OPENAI_API_KEY
        self.model_name = model_name or settings.LLM_MODEL

    async def _call_llm(
        self,
        vendor_name: str,
        evidence_list: List[RetrievalResult],
        user_message: str,
        conversation_history: Optional[List[ChatMessagePayload]] = None
    ) -> str:
        """Invokes OpenAI LLM with grounded RAG context and system prompt."""
        if not self.api_key or not self.api_key.strip():
            raise ValueError(
                "Assistant unavailable — OpenAI API key is not configured. Please supply OPENAI_API_KEY in environment."
            )

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)

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

            system_instruction = (
                f"You are VendorGuard AI Assistant, an expert vendor risk analyst.\n"
                f"Your task is to answer user questions about vendor '{vendor_name}'.\n\n"
                f"CRITICAL GROUNDING RULES:\n"
                f"1. Answer ONLY using the provided policy document evidence below.\n"
                f"2. Do NOT invent facts, assume unstated details, or use external knowledge.\n"
                f"3. If the provided policy evidence is insufficient or does not contain the answer, "
                f"explicitly state: 'There is insufficient evidence in the indexed policy documents for this vendor to answer your request.'\n"
                f"4. Keep your answer professional, objective, concise, and focused on security, privacy, and compliance risks.\n\n"
                f"--- RETRIEVED POLICY EVIDENCE FOR {vendor_name.upper()} ---\n"
                f"{evidence_text}\n"
            )

            messages = [{"role": "system", "content": system_instruction}]

            # Add stateless conversation history if provided
            if conversation_history:
                for msg in conversation_history:
                    role = "user" if msg.role == "user" else "assistant"
                    messages.append({"role": role, "content": msg.content})

            messages.append({"role": "user", "content": user_message})

            response = await client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.1,
            )

            answer_content = response.choices[0].message.content
            return answer_content.strip() if answer_content else "No response generated."

        except Exception as exc:
            logger.error("OpenAI LLM API call failed: %s", str(exc), exc_info=True)
            raise RuntimeError(f"Assistant LLM service failure: {str(exc)}") from exc

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
