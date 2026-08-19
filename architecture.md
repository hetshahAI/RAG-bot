# OMNICORE RAG — System Architecture & Specification

OMNICORE RAG is an AI observability platform, evidence explorer, and interactive workflow canvas built on a modular FastAPI backend and a React + TypeScript visual interface.

---

## 1. High-Level System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                   OMNICORE RAG FRONTEND (Vite + React Flow)            │
│                                                                        │
│  [ Q/A Playground ]     [ Injection Studio ]     [ Documents Manager ] │
│         │                        │                         │           │
│         └────────────────────────┼─────────────────────────┘           │
│                                  ▼                                     │
│                     Centralized Typed API Client                       │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ HTTP Proxy (:3000 -> :8000)
┌──────────────────────────────────▼─────────────────────────────────────┐
│                     FASTAPI MODULAR BACKEND (:8000)                    │
│                                                                        │
│  API Endpoints (/api/v1):                                              │
│  ├── /rag/ask & /rag/runs/{run_id}  (Strict QA & Execution Tracing)   │
│  ├── /retrieval/search              (Candidate Quality Filtering)      │
│  ├── /reindex & /reindex/preview    (Selective Vector Store Indexing)  │
│  ├── /documents & /ingest/*         (Multimodal Parsing & Raw Store)   │
│  └── /vector-store/*                (ChromaDB Collection Operations)   │
│                                                                        │
│  Core Service Layer:                                                   │
│  ├── IngestionService        (TXT, PDF Page Parser, Tesseract OCR)     │
│  ├── ChunkingService         (Recursive Separator, 512c, 64c overlap)  │
│  ├── EmbeddingService        (BAAI/bge-small-en-v1.5, 384 dimensions)  │
│  ├── ChromaVectorService     (Persistent Local Cosine Index)           │
│  ├── RetrievalService        (Threshold 0.50 Candidate Retrieval)     │
│  ├── RAGService              (Orchestration, Grounding Prompt)         │
│  ├── AnswerValidator         (Authentic Citation & Hallucination Guard)│
│  └── ExecutionTracer         (Lifecycle Metrics & Secret Redaction)    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Pipelines & Responsibilities

### A. Grounded Q/A Pipeline (`POST /api/v1/rag/ask`)
```
User Question
     ↓
1. Query Embedding (BAAI/bge-small-en-v1.5 → 384d normalized vector)
     ↓
2. ChromaDB Cosine Search & Candidate-Quality Filter (similarity >= 0.50)
     ↓
3. Context Builder (Format prompt containing ONLY retrieved chunks)
     ↓
4. LLM Reasoning Engine (mlx-community/Qwen3.6-35B-A3B-4bit @ temp 0.0)
   - Determines: "Does retrieved context answer the question?"
   - YES → Formulate answer strictly from context & cite chunks
   - NO  → Return "insufficient_evidence" without using pretrained knowledge
     ↓
5. Answer & Citation Validator
   - Validates JSON schema & non-empty answer
   - Strictly verifies that every citation ID belongs to retrieved candidate chunks
   - Rejects hallucinated chunk IDs & triggers safe abstention
     ↓
6. Unified Response Contract & Full Lifecycle Execution Trace
```

### B. Selective Document Ingestion & Reindexing Flow (`POST /api/v1/reindex`)
```
Raw Documents (TXT, PDF, Images via OCR)
     ↓
Selected Document IDs Filter
     ↓
Deterministic Chunking (chunk_size: 512, chunk_overlap: 64)
     ↓
Dense Embedding Generation (BAAI/bge-small-en-v1.5)
     ↓
Atomic Vector Index Replacement in ChromaDB (rag_documents)
     ↓
Index State Update (backend/data/indexes/index_state.json)
```

---

## 3. Frontend Architecture (`frontend/`)

- **Workflow Canvas Engine**: `@xyflow/react` (React Flow v12) custom nodes with glowing status rings, duration badges, and statistic grids.
- **Trace Adapter**: `traceAdapter.ts` translates backend `RAGExecutionTrace` lifecycle events into interactive visual execution graphs.
- **Studio Adapter**: `studioAdapter.ts` maps backend ingestion and vector storage metrics to a 6-node pipeline.
- **Evidence Explorer**: Interactive chunk inspection with similarity progress bars, page numbers, and inline citation click-to-highlight.
- **Theme**: Dark-first developer palette (`#090d13`, `#0d1117`, `#161b22`, `#21262d`, `#30363d`, `#388bfd`, `#3fb950`, `#d29922`, `#f85149`, `#a371f7`).

---

## 4. Running the Complete System

### Backend
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm run dev
```
Open **`http://localhost:3000`** in your browser.
