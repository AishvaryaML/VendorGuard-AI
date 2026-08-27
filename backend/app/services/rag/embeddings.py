import logging
from abc import ABC, abstractmethod
from typing import List, Optional
from app.core.config import settings

logger = logging.getLogger("vendorguard.rag.embeddings")


class BaseEmbeddingService(ABC):
    """Abstract interface for embedding generation services."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Returns the embedding vector dimension."""
        pass

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Generates embedding vector for a single string."""
        pass

    @abstractmethod
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generates embedding vectors for a batch of strings."""
        pass


class OpenAIEmbeddingService(BaseEmbeddingService):
    """
    OpenAI Embedding API implementation supporting batch embeddings and error handling.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model_name = model_name or settings.EMBEDDING_MODEL

    @property
    def dimension(self) -> int:
        # Default dimension for text-embedding-3-small is 1536
        if "large" in self.model_name:
            return 3072
        return 1536

    async def embed_text(self, text: str) -> List[float]:
        if not text or not text.strip():
            # Return zero vector for empty text
            return [0.0] * self.dimension

        results = await self.embed_documents([text])
        return results[0]

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        cleaned_texts = [t.replace("\n", " ").strip() if t else " " for t in texts]

        if not self.api_key or not self.api_key.strip():
            raise ValueError(
                "Embedding generation unavailable — OpenAI API key is not configured. Please supply OPENAI_API_KEY in environment."
            )

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)
            response = await client.embeddings.create(
                model=self.model_name,
                input=cleaned_texts
            )
            embeddings = [item.embedding for item in response.data]
            return embeddings

        except Exception as exc:
            logger.error("OpenAI Embedding API call failed: %s", str(exc), exc_info=True)
            raise RuntimeError(f"Embedding API call failed: {str(exc)}") from exc
