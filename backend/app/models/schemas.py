from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class HealthResponse(BaseModel):
    """Schema for service health check response."""

    status: str = Field(default="ok", description="Current status of the backend service")
    service: str = Field(default="rag-backend", description="Service identifier")


class TextIngestRequest(BaseModel):
    """Request schema for plain text ingestion."""

    text: str = Field(..., description="Raw text content to ingest")
    title: Optional[str] = Field(default=None, description="Optional title for the document")

    @field_validator("text")
    @classmethod
    def validate_text_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Text content cannot be empty or whitespace only.")
        return v


class DocumentPage(BaseModel):
    """Page metadata and extracted content for paginated documents (e.g. PDF)."""

    page_number: int = Field(..., description="1-indexed page number")
    content: str = Field(..., description="Extracted and normalized text content of this page")
    character_count: int = Field(..., description="Character count for this page")


class OCRMetadata(BaseModel):
    """Metadata extracted during OCR processing."""

    engine: str = Field(..., description="OCR engine utilized")
    format: str = Field(..., description="Image format (e.g. PNG, JPEG, WEBP)")
    width: int = Field(..., description="Image width in pixels")
    height: int = Field(..., description="Image height in pixels")
    original_filename: Optional[str] = Field(default=None, description="Original filename of the image")


class DocumentModel(BaseModel):
    """Internal document representation for raw storage."""

    document_id: str = Field(..., description="Unique document identifier")
    title: Optional[str] = Field(default=None, description="Document title")
    source_type: str = Field(default="text", description="Source format/type (e.g. text, txt, pdf, image)")
    content: str = Field(..., description="Normalized document text content")
    character_count: int = Field(..., description="Total characters in normalized content")
    page_count: Optional[int] = Field(default=None, description="Total number of pages if paginated")
    pages: Optional[List[DocumentPage]] = Field(
        default=None,
        description="List of individual page contents and metadata",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Arbitrary metadata such as OCR or file attributes",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when document was ingested",
    )


class DocumentIngestResponse(BaseModel):
    """Response schema returned after successful document ingestion."""

    document_id: str = Field(..., description="Unique document identifier")
    title: Optional[str] = Field(default=None, description="Document title")
    source_type: str = Field(..., description="Source format/type (e.g. text, txt, pdf, image)")
    character_count: int = Field(..., description="Total characters in normalized content")
    page_count: Optional[int] = Field(default=None, description="Total number of pages if paginated")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional document metadata")
    created_at: datetime = Field(..., description="Timestamp when document was ingested")


# Alias for backward compatibility
TextIngestResponse = DocumentIngestResponse


# ============================================================================
# Document Listing & Selection Schemas (Step 1.6 & 1.7)
# ============================================================================


class DocumentSummary(BaseModel):
    """Summary of an uploaded document including its active indexing status."""

    document_id: str = Field(..., description="Unique document identifier")
    title: Optional[str] = Field(default=None, description="Document title or filename")
    source_type: str = Field(..., description="Source format/type (e.g. text, txt, pdf, image)")
    character_count: int = Field(..., description="Total characters in normalized content")
    page_count: Optional[int] = Field(default=None, description="Total pages if paginated")
    is_active: bool = Field(default=False, description="Whether document is part of the active RAG index")
    created_at: datetime = Field(..., description="Timestamp when document was ingested")


class DocumentListResponse(BaseModel):
    """Response for listing all uploaded documents."""

    total_count: int = Field(..., description="Total number of uploaded raw documents")
    active_count: int = Field(..., description="Total number of documents in active index")
    documents: List[DocumentSummary] = Field(default_factory=list, description="List of document summaries")


class Chunk(BaseModel):
    """A single atomic chunk extracted from a selected document."""

    chunk_id: str = Field(..., description="Deterministic unique chunk identifier")
    document_id: str = Field(..., description="Origin document identifier")
    source_type: str = Field(..., description="Source format/type (e.g. text, txt, pdf, image)")
    title: Optional[str] = Field(default=None, description="Origin document title")
    content: str = Field(..., description="Chunk text content")
    chunk_index: int = Field(..., description="0-indexed sequence of this chunk within the document")
    character_count: int = Field(..., description="Character count in this chunk")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Chunk-level metadata including page numbers, source filenames, OCR attributes",
    )


class ChunkStatistics(BaseModel):
    """Statistical summary of generated chunks."""

    avg_chunk_size: float = Field(..., description="Average character length across all chunks")
    min_chunk_size: int = Field(..., description="Minimum chunk character length")
    max_chunk_size: int = Field(..., description="Maximum chunk character length")
    total_chunks: int = Field(..., description="Total number of generated chunks")
    chunks_by_source_type: Dict[str, int] = Field(
        default_factory=dict,
        description="Breakdown of chunk counts by document source type",
    )


class ReindexPreviewRequest(BaseModel):
    """Request payload to preview reindexing for specific documents."""

    document_ids: List[str] = Field(..., description="List of document IDs to select and chunk")

    @field_validator("document_ids")
    @classmethod
    def validate_document_ids(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("document_ids list cannot be empty.")
        cleaned = [item.strip() for item in v if item and item.strip()]
        if not cleaned:
            raise ValueError("document_ids must contain at least one valid document ID.")
        return cleaned


class ReindexPreviewResponse(BaseModel):
    """Response returned by /reindex/preview showing chunk analysis."""

    selected_document_count: int = Field(..., description="Count of selected documents")
    total_chunk_count: int = Field(..., description="Total count of generated chunks")
    chunk_statistics: ChunkStatistics = Field(..., description="Statistics of generated chunks")
    sample_chunks: List[Chunk] = Field(default_factory=list, description="Sample chunks preview")
    source_documents: List[DocumentSummary] = Field(default_factory=list, description="Selected documents metadata")


class ReindexRequest(BaseModel):
    """Request payload for executing reindexing."""

    document_ids: List[str] = Field(..., description="List of document IDs to index into active knowledge base")

    @field_validator("document_ids")
    @classmethod
    def validate_document_ids(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("document_ids list cannot be empty.")
        seen = set()
        cleaned = []
        for item in v:
            if item and item.strip():
                clean_item = item.strip()
                if clean_item not in seen:
                    seen.add(clean_item)
                    cleaned.append(clean_item)
        if not cleaned:
            raise ValueError("document_ids must contain at least one valid document ID.")
        return cleaned


class ReindexResponse(BaseModel):
    """Structured response returned by POST /reindex."""

    status: str = Field(default="completed", description="Execution status of reindex pipeline")
    indexing_version: str = Field(..., description="Active index schema/version")
    selected_document_count: int = Field(..., description="Number of selected documents")
    chunk_count: int = Field(..., description="Total number of chunks created")
    embedding_count: int = Field(..., description="Total number of embeddings generated")
    indexed_at: datetime = Field(..., description="Timestamp when reindexing completed")
    document_ids: List[str] = Field(..., description="List of active document IDs in the newly replaced index")


class IndexStateModel(BaseModel):
    """Persistent state tracking the active RAG knowledge base."""

    active_document_ids: List[str] = Field(default_factory=list, description="List of active document IDs")
    indexing_version: str = Field(default="v1", description="Indexing schema version")
    chunking_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Chunking parameters used for current index",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when index state was last modified",
    )


# ============================================================================
# Embedding Schemas (Step 1.8)
# ============================================================================


class EmbeddingInfoResponse(BaseModel):
    """Metadata response for current embedding model configuration."""

    model_name: str = Field(..., description="Embedding model identifier (e.g. BAAI/bge-small-en-v1.5)")
    dimension: int = Field(..., description="Dense embedding vector dimension (e.g. 384)")
    device: str = Field(..., description="Active compute device (cpu, cuda)")
    normalize_embeddings: bool = Field(..., description="Whether output vectors are L2 normalized")


class EmbeddingTestRequest(BaseModel):
    """Request payload to test embedding generation."""

    texts: List[str] = Field(..., description="List of strings to embed")

    @field_validator("texts")
    @classmethod
    def validate_texts(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("texts list cannot be empty.")
        cleaned = [t.strip() for t in v if t and t.strip()]
        if not cleaned:
            raise ValueError("texts must contain at least one non-empty string.")
        return cleaned


class EmbeddingItemPreview(BaseModel):
    """Preview of a single text embedding."""

    index: int = Field(..., description="Index of text in batch")
    text_preview: str = Field(..., description="Preview snippet of input text")
    character_count: int = Field(..., description="Character count of input text")
    vector_length: int = Field(..., description="Length of embedding vector")
    sample_vector: List[float] = Field(..., description="Preview slice of vector coordinates")
    vector: Optional[List[float]] = Field(default=None, description="Full embedding vector if requested")


class EmbeddingTestResponse(BaseModel):
    """Response returned by POST /api/v1/embeddings/test."""

    model_name: str = Field(..., description="Embedding model used")
    dimension: int = Field(..., description="Embedding vector dimension")
    text_count: int = Field(..., description="Number of texts embedded")
    device: str = Field(..., description="Device used for inference")
    normalize_embeddings: bool = Field(..., description="Whether vectors are normalized")
    embeddings: List[EmbeddingItemPreview] = Field(default_factory=list, description="Generated embedding items")


# ============================================================================
# Vector Store Schemas (ChromaDB)
# ============================================================================


class VectorStoreInfoResponse(BaseModel):
    """Safe metadata response for vector store collection."""

    provider: str = Field(default="chromadb", description="Vector database provider")
    collection_name: str = Field(..., description="Active vector collection name")
    collection_exists: bool = Field(..., description="Whether collection currently exists on disk")
    vector_dimension: int = Field(default=384, description="Expected vector embedding dimension")
    point_count: int = Field(..., description="Total number of vector points/chunks stored in collection")
    persistence_path: str = Field(..., description="Local filesystem path where collection is stored")


class VectorStoreClearResponse(BaseModel):
    """Response returned when clearing vector store collection."""

    status: str = Field(default="ok", description="Status of clear operation")
    message: str = Field(..., description="Human-readable result message")
    collection_name: str = Field(..., description="Vector collection cleared")
    point_count: int = Field(default=0, description="Remaining point count in collection after clear")


# ============================================================================
# Retrieval Schemas (Step 2.1)
# ============================================================================


class RetrievalRequest(BaseModel):
    """Request payload for semantic knowledge base retrieval."""

    question: str = Field(..., description="User query or question to search within active knowledge base")
    top_k: Optional[int] = Field(default=None, description="Optional override for maximum chunks to return")

    @field_validator("question")
    @classmethod
    def validate_question_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Question cannot be empty or whitespace only.")
        return v.strip()

    @field_validator("top_k")
    @classmethod
    def validate_top_k(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("top_k must be a positive integer greater than 0.")
        return v


class RetrievalChunk(BaseModel):
    """Grounding chunk retrieved from active vector index."""

    chunk_id: str = Field(..., description="Deterministic unique chunk identifier")
    document_id: str = Field(..., description="Origin document identifier")
    title: Optional[str] = Field(default=None, description="Origin document title")
    source_type: str = Field(..., description="Origin source type (txt, pdf, image, text)")
    content: str = Field(..., description="Text content of the retrieved chunk")
    similarity_score: float = Field(..., description="Calculated cosine similarity score (0.0 to 1.0)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Preserved chunk-level metadata")


class RetrievalResponse(BaseModel):
    """Grounding evidence response returned by POST /api/v1/retrieval/search."""

    question: str = Field(..., description="Original search question")
    status: str = Field(..., description="Retrieval outcome ('success' or 'insufficient_evidence')")
    chunks: List[RetrievalChunk] = Field(default_factory=list, description="Relevant context chunks passing threshold")
    chunk_count: int = Field(..., description="Number of context chunks returned")
    threshold: float = Field(..., description="Similarity threshold applied for filtering")
    active_document_count: int = Field(..., description="Count of active documents currently in the indexed knowledge base")


# ============================================================================
# RAG QA & Execution Trace Schemas (Step 2.2)
# ============================================================================


class CitationItem(BaseModel):
    """Structured citation referencing an authentic retrieved chunk."""

    chunk_id: str = Field(..., description="Identifier of the cited chunk")
    document_id: str = Field(..., description="Identifier of the origin document")
    title: Optional[str] = Field(default=None, description="Title or filename of the origin document")


class RAGAskRequest(BaseModel):
    """Request payload to ask a question to the strict grounded RAG QA system."""

    question: str = Field(..., description="User question to answer using active knowledge base")
    top_k: Optional[int] = Field(default=None, description="Optional override for maximum context chunks to retrieve")

    @field_validator("question")
    @classmethod
    def validate_question_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Question cannot be empty or whitespace only.")
        return v.strip()

    @field_validator("top_k")
    @classmethod
    def validate_top_k(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("top_k must be a positive integer greater than 0.")
        return v


class RAGRetrievalDetail(BaseModel):
    """Detailed retrieval context included in RAGAskResponse."""

    status: str = Field(..., description="Retrieval status: 'success' or 'no_candidates'")
    chunk_count: int = Field(..., description="Number of candidate chunks retrieved")
    threshold: float = Field(..., description="Similarity threshold applied during retrieval")
    chunks: List[RetrievalChunk] = Field(default_factory=list, description="Preserved candidate context chunks")


class RAGLLMDetail(BaseModel):
    """Detailed LLM output and citations in RAGAskResponse."""

    status: str = Field(..., description="LLM outcome status: 'answered' or 'insufficient_evidence'")
    answer: str = Field(..., description="Grounded answer text or deterministic abstention message")
    citations: List[CitationItem] = Field(default_factory=list, description="Validated citations to source chunks")


class RAGAskResponse(BaseModel):
    """Grounded answer response returned by POST /api/v1/rag/ask."""

    run_id: str = Field(..., description="Unique execution run identifier")
    status: str = Field(..., description="Overall outcome status: 'answered' or 'insufficient_evidence'")
    question: str = Field(..., description="Original user question")
    retrieval: RAGRetrievalDetail = Field(..., description="Full retrieval details and candidate chunks")
    llm: RAGLLMDetail = Field(..., description="LLM analysis, answer, and citations")


class RAGTraceEvent(BaseModel):
    """Individual lifecycle node event within a RAG execution trace."""

    event_id: str = Field(..., description="Unique trace event identifier")
    node: str = Field(
        ...,
        description="Pipeline node: query, embedding, retrieval, evidence_gate, context_builder, llm, validator, answer",
    )
    status: str = Field(..., description="Event status: started | processing | completed | failed | skipped")
    started_at: datetime = Field(..., description="Timestamp when node execution started")
    completed_at: datetime = Field(..., description="Timestamp when node execution ended")
    duration_ms: float = Field(..., description="Execution duration in milliseconds")
    details: Dict[str, Any] = Field(default_factory=dict, description="Safe execution metadata (secrets sanitized)")


class RAGExecutionTrace(BaseModel):
    """Full execution trace of a RAG query run for transparency and auditability."""

    run_id: str = Field(..., description="Unique execution run identifier")
    question: str = Field(..., description="Original user question")
    active_document_count: int = Field(..., description="Number of active documents in knowledge base during run")
    events: List[RAGTraceEvent] = Field(default_factory=list, description="Sequential lifecycle trace events")
