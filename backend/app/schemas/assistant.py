from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field


class ChatMessagePayload(BaseModel):
    role: str = Field(..., description="Role of message sender ('user' or 'assistant').")
    content: str = Field(..., description="Text content of the message.")


class AssistantCitation(BaseModel):
    document_type: str
    title: str
    source_url: str
    snippet: str
    similarity_score: float
    chunk_id: str


class AssistantChatRequest(BaseModel):
    vendor_id: str = Field(..., description="Target vendor ID for context isolation.")
    message: str = Field(..., description="User natural language question.")
    conversation_history: Optional[List[ChatMessagePayload]] = Field(
        default=None,
        description="Optional stateless multi-turn conversation history."
    )


class AssistantChatResponse(BaseModel):
    vendor_id: str
    answer: str
    sources: List[AssistantCitation]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
