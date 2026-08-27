# VendorGuard AI — Phase 6.1 RAG Foundation Documentation

## Overview

Phase 6.1 introduces a modular **Retrieval-Augmented Generation (RAG)** foundation into VendorGuard AI. The goal of the RAG layer is to enable fine-grained, evidence-backed semantic search over discovered vendor policy documents (Privacy Policies, Terms of Service, Security Centers, DPAs, Compliance Docs).

This RAG foundation serves as the core semantic retrieval subsystem for:
* **Phase 6.2**: VendorGuard AI Assistant API (`POST /api/v1/assistant/chat`).
* **Phase 6.3**: Autonomous Agentic Risk Auditing (LangGraph agents).

---

## RAG Architecture Pipeline

```text
Vendor
  │
  ▼
Stored Policy Document (Document + PolicyVersion)
  │
  ▼
Text Extraction (raw_content)
  │
  ▼
Text Chunking (TextChunker)
  │
  ▼
Embedding Generation (OpenAIEmbeddingService)
  │
  ▼
Vector Storage (InMemoryVectorStore / BaseVectorStore)
  │
  ▼
Similarity Search (RAGRetriever)
  │
  ▼
Retrieved Evidence (RetrievalResult with Citations)
```

---

## Core Components

### 1. Document Chunking (`app.services.rag.chunker.TextChunker`)
* **Algorithm**: Sentence & paragraph-aware recursive boundary splitter.
* **Defaults**: `chunk_size = 1000` tokens/words, `chunk_overlap = 150` tokens/words.
* **Ordering & Identifiers**: Generates stable `chunk_index` (0, 1, 2...) and SHA-256 `content_hash` per chunk.
* **Relational Persistence**: Stores chunk metadata in the `document_chunks` table (`DocumentChunk` model).

### 2. Embeddings (`app.services.rag.embeddings.OpenAIEmbeddingService`)
* **Interface**: `BaseEmbeddingService` for easy provider swapping.
* **Default Model**: OpenAI `text-embedding-3-small` (1536-dimensional vectors).
* **Batch Processing**: Supports batch embedding for efficient document indexing.
* **Mock Capability**: Fully mockable in tests without internet or real API keys.

### 3. Vector Storage (`app.services.rag.vector_store`)
* **Interface**: `BaseVectorStore` abstract base class defining `add_records`, `delete_records`, `search`, `count`, and `clear`.
* **Current Implementation**: `InMemoryVectorStore` using cosine similarity search.
* **Future Extension**: Designed for zero-rewiring migration to **Pinecone** or **PostgreSQL + pgvector**.

### 4. RAG Indexer (`app.services.rag.indexer.RAGIndexer`)
* **Entry points**: `index_policy_version`, `index_document`, `index_vendor_documents`.
* **Duplicate Prevention**: Detects if a `PolicyVersion` has already been indexed. If unchanged, duplicate vector generation is skipped.
* **Clean Re-indexing**: When `force_reindex=True` or text changes, old `DocumentChunk` DB records and vector records are purged before adding new ones.

### 5. RAG Retriever (`app.services.rag.retriever.RAGRetriever`)
* **Strict Vendor Isolation**: Enforces filtering by `vendor_id` during similarity search. A query for Vendor A will **never** return candidate chunks from Vendor B.
* **Document Traceability**: Every returned `RetrievalResult` includes:
  * `vendor_id` & `vendor_name`
  * `document_id` & `policy_version_id`
  * `document_type` & `source_url`
  * `chunk_id` & `chunk_index`
  * `content_hash` & `similarity_score`
  * `text` (retrieved snippet)

---

## API Endpoints (Development & Verification Only)

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/rag/index/{vendor_id}` | POST | Triggers manual RAG indexing for all documents of a vendor. |
| `/api/v1/rag/search` | POST | Executes vendor-isolated semantic similarity search. |

*Note: The assistant endpoint `POST /api/v1/assistant/chat` will be implemented in Phase 6.2.*

---

## Migration Path to External Vector Databases

To replace `InMemoryVectorStore` with Pinecone or pgvector in future phases:
1. Subclass `BaseVectorStore` (e.g. `PineconeVectorStore`).
2. Implement `add_records`, `delete_records`, and `search` using the provider's SDK.
3. Update `get_vector_store()` in `vector_store.py` or set `VECTOR_STORE_TYPE` in `.env`.
