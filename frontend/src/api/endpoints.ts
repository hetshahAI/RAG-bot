import { request } from "./client";
import {
  DocumentIngestResponse,
  DocumentListResponse,
  EmbeddingInfoResponse,
  EmbeddingTestResponse,
  HealthResponse,
  IndexStateModel,
  RAGAskResponse,
  RAGExecutionTrace,
  ReindexPreviewResponse,
  ReindexResponse,
  RetrievalResponse,
  RootMetadataResponse,
  VectorStoreClearResponse,
  VectorStoreInfoResponse,
} from "../types/backend";

export const api = {
  // Health & Metadata
  getHealth: () => request<HealthResponse>("/health"),
  getRootInfo: () => request<RootMetadataResponse>("/"),

  // Documents & Ingestion
  ingestText: (text: string, title?: string) =>
    request<DocumentIngestResponse>("/api/v1/ingest/text", {
      method: "POST",
      body: JSON.stringify({ text, title }),
    }),

  ingestFile: (file: File, title?: string) => {
    const formData = new FormData();
    formData.append("file", file);
    if (title) {
      formData.append("title", title);
    }
    return request<DocumentIngestResponse>("/api/v1/ingest/file", {
      method: "POST",
      body: formData,
    });
  },

  getDocuments: () => request<DocumentListResponse>("/api/v1/documents"),

  // Selective Indexing & Reindex
  previewReindex: (documentIds: string[]) =>
    request<ReindexPreviewResponse>("/api/v1/reindex/preview", {
      method: "POST",
      body: JSON.stringify({ document_ids: documentIds }),
    }),

  executeReindex: (documentIds: string[]) =>
    request<ReindexResponse>("/api/v1/reindex", {
      method: "POST",
      body: JSON.stringify({ document_ids: documentIds }),
    }),

  getIndexState: () => request<IndexStateModel>("/api/v1/reindex/state"),

  // Embedding Services
  getEmbeddingInfo: () => request<EmbeddingInfoResponse>("/api/v1/embeddings/info"),

  testEmbedding: (texts: string[]) =>
    request<EmbeddingTestResponse>("/api/v1/embeddings/test", {
      method: "POST",
      body: JSON.stringify({ texts }),
    }),

  // Vector Store (ChromaDB)
  getVectorStoreInfo: () => request<VectorStoreInfoResponse>("/api/v1/vector-store/info"),

  clearVectorStore: () =>
    request<VectorStoreClearResponse>("/api/v1/vector-store/clear", {
      method: "POST",
    }),

  // Diagnostic Retrieval
  searchRetrieval: (question: string, top_k?: number) =>
    request<RetrievalResponse>("/api/v1/retrieval/search", {
      method: "POST",
      body: JSON.stringify({ question, top_k }),
    }),

  // Production Grounded RAG QA
  askRAG: (question: string, top_k?: number) =>
    request<RAGAskResponse>("/api/v1/rag/ask", {
      method: "POST",
      body: JSON.stringify({ question, top_k }),
    }),

  // Execution Trace
  getRunTrace: (runId: string) =>
    request<RAGExecutionTrace>(`/api/v1/rag/runs/${encodeURIComponent(runId)}`),
};
