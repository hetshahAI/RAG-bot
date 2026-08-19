/**
 * TypeScript definitions mapping directly to backend schemas in app/models/schemas.py
 */

export interface HealthResponse {
  status: string;
  service: string;
}

export interface RootMetadataResponse {
  service: string;
  version: string;
  status: string;
  docs: string;
  health: string;
}

export interface DocumentPage {
  page_number: number;
  content: string;
  character_count: number;
}

export interface OCRMetadata {
  engine: string;
  format: string;
  width: number;
  height: number;
  original_filename?: string | null;
}

export interface DocumentModel {
  document_id: string;
  title?: string | null;
  source_type: string;
  content: string;
  character_count: number;
  page_count?: number | null;
  pages?: DocumentPage[] | null;
  metadata?: Record<string, any> | null;
  created_at: string;
}

export interface DocumentIngestResponse {
  document_id: string;
  title?: string | null;
  source_type: string;
  character_count: number;
  page_count?: number | null;
  metadata?: Record<string, any> | null;
  created_at: string;
}

export interface DocumentSummary {
  document_id: string;
  title?: string | null;
  source_type: string;
  character_count: number;
  page_count?: number | null;
  is_active: boolean;
  created_at: string;
}

export interface DocumentListResponse {
  total_count: number;
  active_count: number;
  documents: DocumentSummary[];
}

export interface Chunk {
  chunk_id: string;
  document_id: string;
  source_type: string;
  title?: string | null;
  content: string;
  chunk_index: number;
  character_count: number;
  metadata: Record<string, any>;
}

export interface ChunkStatistics {
  avg_chunk_size: number;
  min_chunk_size: number;
  max_chunk_size: number;
  total_chunks: number;
  chunks_by_source_type: Record<string, number>;
}

export interface ReindexPreviewResponse {
  selected_document_count: number;
  total_chunk_count: number;
  chunk_statistics: ChunkStatistics;
  sample_chunks: Chunk[];
  source_documents: DocumentSummary[];
}

export interface ReindexResponse {
  status: string;
  indexing_version: string;
  selected_document_count: number;
  chunk_count: number;
  embedding_count: number;
  indexed_at: string;
  document_ids: string[];
}

export interface IndexStateModel {
  active_document_ids: string[];
  indexing_version: string;
  chunking_config: {
    chunk_size?: number;
    chunk_overlap?: number;
    separator?: string;
    [key: string]: any;
  };
  updated_at: string;
}

export interface EmbeddingInfoResponse {
  model_name: string;
  dimension: number;
  device: string;
  normalize_embeddings: boolean;
}

export interface EmbeddingItemPreview {
  index: number;
  text_preview: string;
  character_count: number;
  vector_length: number;
  sample_vector: number[];
  vector?: number[] | null;
}

export interface EmbeddingTestResponse {
  model_name: string;
  dimension: number;
  text_count: number;
  device: string;
  normalize_embeddings: boolean;
  embeddings: EmbeddingItemPreview[];
}

export interface VectorStoreInfoResponse {
  provider: string;
  collection_name: string;
  collection_exists: boolean;
  vector_dimension: number;
  point_count: number;
  persistence_path: string;
}

export interface VectorStoreClearResponse {
  status: string;
  message: string;
  collection_name: string;
  point_count: number;
}

export interface RetrievalChunk {
  chunk_id: string;
  document_id: string;
  title?: string | null;
  source_type: string;
  content: string;
  similarity_score: number;
  metadata: Record<string, any>;
}

export interface RetrievalResponse {
  question: string;
  status: string; // 'success' | 'no_candidates'
  chunks: RetrievalChunk[];
  chunk_count: number;
  threshold: number;
  active_document_count: number;
}

export interface CitationItem {
  chunk_id: string;
  document_id: string;
  title?: string | null;
}

export interface RAGRetrievalDetail {
  status: string; // 'success' | 'no_candidates'
  chunk_count: number;
  threshold: number;
  chunks: RetrievalChunk[];
}

export interface RAGLLMDetail {
  status: string; // 'answered' | 'insufficient_evidence'
  answer: string;
  citations: CitationItem[];
}

export interface RAGAskResponse {
  run_id: string;
  status: string; // 'answered' | 'insufficient_evidence'
  question: string;
  retrieval: RAGRetrievalDetail;
  llm: RAGLLMDetail;
}

export interface RAGTraceEvent {
  event_id: string;
  node: string; // 'query' | 'embedding' | 'retrieval' | 'context_builder' | 'llm' | 'validator' | 'answer'
  status: string; // 'started' | 'processing' | 'completed' | 'failed' | 'skipped'
  started_at: string;
  completed_at: string;
  duration_ms: number;
  details: Record<string, any>;
}

export interface RAGExecutionTrace {
  run_id: string;
  question: string;
  active_document_count: number;
  events: RAGTraceEvent[];
}
