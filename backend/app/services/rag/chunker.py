import re
import hashlib
import uuid
from dataclasses import dataclass
from typing import List, Optional
from app.core.config import settings


@dataclass
class ChunkData:
    chunk_id: str
    chunk_index: int
    text: str
    content_hash: str
    token_count: int


class TextChunker:
    """
    Sentence and paragraph-aware text chunking service for legal/policy documents.
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None
    ):
        self.chunk_size = chunk_size or settings.RAG_CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.RAG_CHUNK_OVERLAP

    def _estimate_words(self, text: str) -> int:
        return len(text.split())

    def _split_into_sentences(self, text: str) -> List[str]:
        """Splits text into meaningful sentences or line blocks while preserving context."""
        # Split on double line breaks (paragraphs) or sentence delimiters (. ! ?) followed by whitespace
        raw_units = re.split(r"(?<=[.!?])\s+|\n\n+", text)
        clean_units = [u.strip() for u in raw_units if u and u.strip()]
        return clean_units

    def chunk_text(self, text: str, policy_version_id: Optional[str] = None) -> List[ChunkData]:
        """
        Splits clean document text into ordered chunks with configured size and overlap.
        Assigns stable chunk_index, content_hash, and chunk_id.
        """
        if not text or not text.strip():
            return []

        sentences = self._split_into_sentences(text)
        if not sentences:
            return []

        chunks_text: List[str] = []
        current_chunk_words: List[str] = []
        current_word_count = 0

        for sentence in sentences:
            words = sentence.split()
            sentence_word_count = len(words)

            if not words:
                continue

            # Handle case where a single sentence exceeds chunk_size
            if sentence_word_count > self.chunk_size:
                # Flush current accumulated chunk if any
                if current_chunk_words:
                    chunks_text.append(" ".join(current_chunk_words))
                    current_chunk_words = []
                    current_word_count = 0
                
                # Split large sentence by words directly
                for i in range(0, sentence_word_count, self.chunk_size - self.chunk_overlap):
                    sub_words = words[i : i + self.chunk_size]
                    if sub_words:
                        chunks_text.append(" ".join(sub_words))
                continue

            if current_word_count + sentence_word_count > self.chunk_size:
                # Store current chunk
                chunks_text.append(" ".join(current_chunk_words))
                
                # Prepare overlap for next chunk from trailing words of current chunk
                overlap_count = min(self.chunk_overlap, len(current_chunk_words))
                if overlap_count > 0:
                    overlap_words = current_chunk_words[-overlap_count:]
                    current_chunk_words = overlap_words + words
                    current_word_count = len(current_chunk_words)
                else:
                    current_chunk_words = words
                    current_word_count = sentence_word_count
            else:
                current_chunk_words.extend(words)
                current_word_count += sentence_word_count

        if current_chunk_words:
            chunks_text.append(" ".join(current_chunk_words))

        result_chunks: List[ChunkData] = []
        for idx, chunk_str in enumerate(chunks_text):
            chunk_str = chunk_str.strip()
            if not chunk_str:
                continue

            chunk_hash = hashlib.sha256(chunk_str.encode("utf-8")).hexdigest()
            
            # Generate stable chunk_id if policy_version_id provided
            if policy_version_id:
                id_seed = f"{policy_version_id}:{idx}:{chunk_hash[:16]}"
                chunk_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, id_seed))
            else:
                chunk_id = str(uuid.uuid4())

            token_est = self._estimate_words(chunk_str)

            result_chunks.append(
                ChunkData(
                    chunk_id=chunk_id,
                    chunk_index=idx,
                    text=chunk_str,
                    content_hash=chunk_hash,
                    token_count=token_est,
                )
            )

        return result_chunks
