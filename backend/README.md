# RAG Pipeline - Backend

FastAPI-powered backend foundation for the modular RAG pipeline.

## Features

- **FastAPI Framework**: High performance async web framework with automatic OpenAPI documentation.
- **Hierarchical Configuration**: Non-secret configurations in `config.yaml` and environment variables / secrets in `.env`.
- **Modular Directory Structure**: Separated concerns for `api`, `core`, `models`, `services`, `db`, and `data`.
- **Pydantic V2 Models**: Type safety and validation for request/response schemas and application settings.
- **Production-Ready**: Clean lifespan logging, CORS middleware, and standardized health check endpoints.

---

## Directory Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                     # Application entry point & FastAPI factory
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py           # v1 Router aggregator
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           └── health.py       # Health check route
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py               # Unified config loader (config.yaml + .env)
│   ├── db/
│   │   └── __init__.py             # Vector database client & lifecycle placeholder
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py              # Pydantic schemas (HealthResponse, etc.)
│   └── services/
│       └── __init__.py             # RAG services (Ingestion, Embedding, Retrieval, LLM)
├── config.yaml                     # Non-secret RAG pipeline configuration
├── data/
│   ├── raw/                        # Unprocessed documents storage
│   ├── processed/                  # Chunked/processed data storage
│   └── indexes/                    # Local index/cache storage
├── .env.example                    # Environment secrets template
├── .env                            # Active environment file
├── .gitignore                      # Git ignore file
├── requirements.txt                # Python dependencies
└── README.md                       # Setup and usage documentation
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- `pip` or virtual environment tool

### 1. Create and Activate Virtual Environment

**Windows (PowerShell):**
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment & Configuration

Copy the example environment file:
```bash
cp .env.example .env
```

- **`config.yaml`**: Contains non-secret settings such as the embedding model (`BAAI/bge-small-en-v1.5`), chunking parameters, and vector database collection defaults.
- **`.env`**: Contains sensitive keys, database URLs, and environment flags.

---

## Running the Application

### Development Server

From the `backend/` directory:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be accessible at:
- Root URL: `http://localhost:8000/`
- Health Endpoint: `http://localhost:8000/health`
- Swagger UI Documentation: `http://localhost:8000/docs`
- ReDoc Documentation: `http://localhost:8000/redoc`

---

## API Endpoints

### 1. Health Check
`GET /health` or `GET /api/v1/health`

**Response (`200 OK`):**
```json
{
  "status": "ok",
  "service": "rag-backend"
}
```

### 2. Ingest Plain Text
`POST /api/v1/ingest/text`

**Request Body (`application/json`):**
```json
{
  "text": "Your plain text content goes here.",
  "title": "Optional Document Title"
}
```

**Response (`201 Created`):**
```json
{
  "document_id": "doc_2d501b9ba3b44703886395e2b7fcbc95",
  "title": "Optional Document Title",
  "source_type": "text",
  "character_count": 34,
  "created_at": "2026-08-19T08:18:44.277207Z"
}
```

### 3. Ingest Document or Image File (.txt / .pdf / .png / .jpg / .jpeg / .webp)
`POST /api/v1/ingest/file`

Accepts a single `.txt`, `.pdf`, or image file (`.png`, `.jpg`, `.jpeg`, `.webp`) via `multipart/form-data`.
- For **PDF files**: Text is extracted page-by-page, preserving page boundaries in both content and structured metadata.
- For **Images**: Optical Character Recognition (OCR) is performed via the configured OCR engine (e.g. Tesseract), extracting normalized text and saving image metadata (format, dimensions, engine).

**cURL Example (TXT):**
```bash
curl -X POST http://127.0.0.1:8000/api/v1/ingest/file \
  -F "file=@/path/to/document.txt"
```

**cURL Example (PDF):**
```bash
curl -X POST http://127.0.0.1:8000/api/v1/ingest/file \
  -F "file=@/path/to/manual.pdf"
```

**cURL Example (Image / OCR):**
```bash
curl -X POST http://127.0.0.1:8000/api/v1/ingest/file \
  -F "file=@/path/to/receipt.png"
```

**Response (`201 Created` - Image OCR):**
```json
{
  "document_id": "doc_f7a8b9c0d1e2...",
  "title": "receipt.png",
  "source_type": "image",
  "character_count": 320,
  "page_count": null,
  "metadata": {
    "engine": "tesseract",
    "format": "PNG",
    "width": 1200,
    "height": 800,
    "original_filename": "receipt.png"
  },
  "created_at": "2026-08-19T08:40:00.000000Z"
}
```

### 4. List Uploaded Documents
`GET /api/v1/documents`

Lists all uploaded raw documents in storage along with their active indexing state (`is_active`).

**Response (`200 OK`):**
```json
{
  "total_count": 2,
  "active_count": 1,
  "documents": [
    {
      "document_id": "doc_f7a8b9c0d1e2...",
      "title": "receipt.png",
      "source_type": "image",
      "character_count": 320,
      "page_count": null,
      "is_active": false,
      "created_at": "2026-08-19T08:40:00.000000Z"
    },
    {
      "document_id": "doc_e48fa910d517...",
      "title": "manual.pdf",
      "source_type": "pdf",
      "character_count": 4820,
      "page_count": 5,
      "is_active": true,
      "created_at": "2026-08-19T08:35:00.000000Z"
    }
  ]
}
```

### 5. Preview Reindexing / Chunking (Selective Indexing)
`POST /api/v1/reindex/preview`

Performs deterministic chunking **only** on explicitly selected documents. Does **not** compute embeddings or modify Qdrant.

**Request Body (`application/json`):**
```json
{
  "document_ids": [
    "doc_e48fa910d517...",
    "doc_f7a8b9c0d1e2..."
  ]
}
```

**Response (`200 OK`):**
```json
{
  "selected_document_count": 2,
  "total_chunk_count": 12,
  "chunk_statistics": {
    "avg_chunk_size": 428.5,
    "min_chunk_size": 180,
    "max_chunk_size": 512,
    "total_chunks": 12,
    "chunks_by_source_type": {
      "pdf": 10,
      "image": 2
    }
  },
  "sample_chunks": [
    {
      "chunk_id": "doc_e48fa910d517..._c0000",
      "document_id": "doc_e48fa910d517...",
      "source_type": "pdf",
      "title": "manual.pdf",
      "content": "Chapter 1: Overview...",
      "chunk_index": 0,
      "character_count": 510,
      "metadata": {
        "page_number": 1,
        "source_type": "pdf",
        "title": "manual.pdf"
      }
    }
  ],
  "source_documents": [ ... ]
}
```

### 6. Execute Reindexing (Replace Active Knowledge Base)
`POST /api/v1/reindex`

Executes the atomic reindexing pipeline for the selected documents (Chunking → Embedding → Vector Index Replacement → State Commit). Replaces the existing active index.

**Request Body (`application/json`):**
```json
{
  "document_ids": [
    "doc_cfe28e389e4f4a3298886b3bf991e26e",
    "doc_e48fa910d51740fa9bd77e387f3747b0"
  ]
}
```

**Response (`200 OK`):**
```json
{
  "status": "completed",
  "indexing_version": "v1",
  "selected_document_count": 2,
  "chunk_count": 8,
  "embedding_count": 8,
  "indexed_at": "2026-08-19T08:50:00.000000Z",
  "document_ids": [
    "doc_cfe28e389e4f4a3298886b3bf991e26e",
    "doc_e48fa910d51740fa9bd77e387f3747b0"
  ]
}
```

### 7. Clear Active Index Selection
`POST /api/v1/reindex/clear`

Clears active document selection from index state without deleting raw uploaded documents.

**Response (`200 OK`):**
```json
{
  "status": "ok",
  "message": "Active index set cleared successfully.",
  "active_count": 0
}
```

### 8. Embedding Model Metadata
`GET /api/v1/embeddings/info`

Retrieve configuration and metadata of the active dense vector embedding model.

**Response (`200 OK`):**
```json
{
  "model_name": "BAAI/bge-small-en-v1.5",
  "dimension": 384,
  "device": "cpu",
  "normalize_embeddings": true
}
```

### 9. Test Embedding Generation
`POST /api/v1/embeddings/test`

Generate dense embeddings for a test list of texts and inspect vector dimensions and normalized sample coordinates.

**Request Body (`application/json`):**
```json
{
  "texts": [
    "Hello world",
    "RAG pipeline architecture with BGE embeddings"
  ]
}
```

**Response (`200 OK`):**
```json
{
  "model_name": "BAAI/bge-small-en-v1.5",
  "dimension": 384,
  "text_count": 2,
  "device": "cpu",
  "normalize_embeddings": true,
  "embeddings": [
    {
      "index": 0,
      "text_preview": "Hello world",
      "character_count": 11,
      "vector_length": 384,
      "sample_vector": [-0.012345, 0.045678, -0.089123, 0.034567, 0.012398]
    },
    {
      "index": 1,
      "text_preview": "RAG pipeline architecture with BGE embeddings",
      "character_count": 45,
      "vector_length": 384,
      "sample_vector": [0.034125, -0.012456, 0.078912, -0.045123, 0.067123]
    }
  ]
}
```

### 10. Vector Store Collection Info
`GET /api/v1/vector-store/info`

Retrieve status, point count, and persistence details of the local ChromaDB vector database.

**Response (`200 OK`):**
```json
{
  "provider": "chromadb",
  "collection_name": "rag_documents",
  "collection_exists": true,
  "vector_dimension": 384,
  "point_count": 8,
  "persistence_path": "C:\\Users\\Het Shah\\Desktop\\Rag-pipeline\\backend\\data\\indexes\\chroma"
}
```

### 11. Clear Vector Store Collection
`POST /api/v1/vector-store/clear`

Truncate/reset the vector database collection points. Does **not** delete uploaded documents from `data/raw/`.

**Response (`200 OK`):**
```json
{
  "status": "ok",
  "message": "ChromaDB collection 'rag_documents' cleared successfully.",
  "collection_name": "rag_documents",
  "point_count": 0
}
```

### 12. Strict Knowledge-Base Retrieval
`POST /api/v1/retrieval/search`

Retrieve grounded evidence chunks matching a user question strictly from active indexed documents in ChromaDB.

**Request Body (`application/json`):**
```json
{
  "question": "What embedding model does this pipeline use?",
  "top_k": 5
}
```

**Response (`200 OK` - Sufficient Evidence):**
```json
{
  "question": "What embedding model does this pipeline use?",
  "status": "success",
  "chunks": [
    {
      "chunk_id": "chunk_doc_cfe28e389e4f4a3298886b3bf991e26e_0",
      "document_id": "doc_cfe28e389e4f4a3298886b3bf991e26e",
      "title": "architecture_guide.txt",
      "source_type": "txt",
      "content": "BAAI/bge-small-en-v1.5 is the active dense vector embedding model, generating 384-dimensional normalized vectors.",
      "similarity_score": 0.8842,
      "metadata": {
        "page_number": 1
      }
    }
  ],
  "chunk_count": 1,
  "threshold": 0.6,
  "active_document_count": 2
}
```

**Response (`200 OK` - Insufficient Evidence / Abstention):**
```json
{
  "question": "What is the recipe for chocolate sourdough?",
  "status": "insufficient_evidence",
  "chunks": [],
  "chunk_count": 0,
  "threshold": 0.6,
  "active_document_count": 2
}
```

### 13. Strict Grounded RAG Question Answering
`POST /api/v1/rag/ask`

Answer questions grounded strictly in the active knowledge base with evidence gating, structured LLM generation, citation validation, and deterministic abstention.

**Request Body (`application/json`):**
```json
{
  "question": "What embedding model does this pipeline use?",
  "top_k": 5
}
```

**Response (`200 OK` - Answered with Grounded Evidence):**
```json
{
  "run_id": "run_ad24fca0979e45178cc50fc4010ce653",
  "status": "answered",
  "answer": "The pipeline utilizes the BAAI/bge-small-en-v1.5 embedding model with 384 dimensions.",
  "citations": [
    {
      "chunk_id": "chunk_doc_cfe28e389e4f4a3298886b3bf991e26e_0",
      "document_id": "doc_cfe28e389e4f4a3298886b3bf991e26e",
      "title": "architecture_guide.txt"
    }
  ],
  "retrieval": {
    "chunk_count": 1,
    "threshold": 0.6
  }
}
```

**Response (`200 OK` - Insufficient Evidence / Deterministic Abstention):**
```json
{
  "run_id": "run_9381ea209bc14299b8b0959ce2a67732",
  "status": "insufficient_evidence",
  "answer": "I don't have enough information in the selected knowledge base to answer this question.",
  "citations": [],
  "retrieval": {
    "chunk_count": 0,
    "threshold": 0.6
  }
}
```

### 14. RAG Execution Run Trace
`GET /api/v1/rag/runs/{run_id}`

Retrieve full execution trace and timing metrics across all 8 lifecycle nodes (`query`, `embedding`, `retrieval`, `evidence_gate`, `context_builder`, `llm`, `validator`, `answer`).

**Response (`200 OK`):**
```json
{
  "run_id": "run_ad24fca0979e45178cc50fc4010ce653",
  "question": "What embedding model does this pipeline use?",
  "active_document_count": 1,
  "events": [
    {
      "event_id": "evt_2d4d989f5bc3",
      "node": "query",
      "status": "completed",
      "started_at": "2026-08-19T10:25:00.000Z",
      "completed_at": "2026-08-19T10:25:00.002Z",
      "duration_ms": 2.1,
      "details": { "question": "What embedding model does this pipeline use?" }
    },
    {
      "event_id": "evt_7f8a9b0c1d2e",
      "node": "llm",
      "status": "completed",
      "started_at": "2026-08-19T10:25:00.350Z",
      "completed_at": "2026-08-19T10:25:01.200Z",
      "duration_ms": 850.0,
      "details": { "model": "mlx-community/Qwen3.6-35B-A3B-4bit", "provider": "openai-compatible" }
    }
  ]
}
```

### 15. Root Metadata
`GET /`

**Response (`200 OK`):**
```json
{
  "service": "RAG Pipeline Backend",
  "version": "0.1.0",
  "status": "online",
  "docs": "/docs",
  "health": "/health"
}
```

---

## RAG Responsibility Model & Grounding Architecture

```
User Question
     ↓
1. Query Embedding (BAAI/bge-small-en-v1.5)
     ↓
2. Active ChromaDB Vector Search (cosine metric)
     ↓
3. Candidate Quality Filtering (similarity_threshold: 0.50)
     ↓
4. Context Builder (Strict prompt containing ONLY retrieved chunks)
     ↓
5. LLM Answerability Analysis & Synthesis:
   "Does the retrieved context contain enough factual information to answer?"
     ├── YES → Formulate answer strictly from context & cite chunks
     └── NO  → Return "insufficient_evidence" without using pretrained knowledge
     ↓
6. Answer Validator (JSON validation, non-empty text, authentic chunk citation checking)
     ↓
7. Unified Response & Execution Tracer:
   - Exposes BOTH full retrieval context (chunks) and LLM output
   - Enables n8n-style visual node inspection in the frontend
```

---

## Vector Database Architecture (ChromaDB)

- **Engine**: Local Persistent [ChromaDB](https://www.trychroma.com/) (`chromadb.PersistentClient`).
- **Location**: `backend/data/indexes/chroma/` (no cloud or network credentials required).
- **Collection Name**: `rag_documents` (configured via `config.yaml`).
- **Distance Metric**: `cosine` (`{"hnsw:space": "cosine"}`).
- **Vector Dimension**: `384` (aligned with `BAAI/bge-small-en-v1.5`).
- **Replacement Semantics**: Atomic reindexing drops and recreates the collection, ensuring the active vector index strictly matches only the currently selected documents.
- **Verification**: You can verify the vector store status anytime using `GET /api/v1/vector-store/info`.

---

## Next Steps

- **Next.js Web Frontend**: n8n-inspired visual RAG playground, document management dashboard, citation previewer, and execution trace visualizer.
