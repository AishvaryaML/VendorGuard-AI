import logging
import httpx
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


class OllamaEmbeddingService(BaseEmbeddingService):
    """
    Local Ollama Embedding API implementation using httpx.
    Dynamically detects and caches vector dimension from returned embedding vectors.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model_name = model_name or settings.OLLAMA_EMBEDDING_MODEL
        self._detected_dimension: Optional[int] = None

    @property
    def dimension(self) -> int:
        # Return cached dimension if available, otherwise default to 768 for nomic-embed-text
        return self._detected_dimension if self._detected_dimension is not None else 768

    async def embed_text(self, text: str) -> List[float]:
        if not text or not text.strip():
            return [0.0] * self.dimension

        results = await self.embed_documents([text])
        return results[0]

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        cleaned_texts = [t.replace("\n", " ").strip() if t else " " for t in texts]
        results: List[List[float]] = []

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Try new Ollama /api/embed batch endpoint first
                embed_res = await client.post(
                    f"{self.base_url}/api/embed",
                    json={
                        "model": self.model_name,
                        "input": cleaned_texts
                    }
                )

                if embed_res.status_code == 200:
                    data = embed_res.json()
                    embeddings = data.get("embeddings", [])
                    if embeddings:
                        self._detected_dimension = len(embeddings[0])
                        return embeddings

                # Fallback to single-item /api/embeddings for legacy Ollama versions
                for text in cleaned_texts:
                    resp = await client.post(
                        f"{self.base_url}/api/embeddings",
                        json={
                            "model": self.model_name,
                            "prompt": text
                        }
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    emb = data.get("embedding", [])
                    if emb and self._detected_dimension is None:
                        self._detected_dimension = len(emb)
                    results.append(emb)

                return results

        except Exception as exc:
            logger.error("Ollama Embedding API call failed: %s", str(exc), exc_info=True)
            raise RuntimeError(f"Ollama embedding failure: {str(exc)}") from exc


def get_embedding_service() -> BaseEmbeddingService:
    """Factory function returning the configured embedding provider service."""
    provider = settings.AI_PROVIDER.lower().strip()
    if provider == "ollama":
        return OllamaEmbeddingService()
    elif provider == "openai":
        return OpenAIEmbeddingService()
    else:
        raise ValueError(
            f"Invalid AI_PROVIDER '{settings.AI_PROVIDER}'. Supported providers are 'ollama' or 'openai'."
        )
