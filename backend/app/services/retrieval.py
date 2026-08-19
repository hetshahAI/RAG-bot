import logging
from typing import Optional

from app.core.config import RetrievalConfig, settings
from app.models.schemas import RetrievalChunk, RetrievalResponse
from app.services.chroma import get_vector_index_service
from app.services.embeddings import get_embedding_service
from app.services.index_state import get_index_state_service
from app.services.interfaces import (
    IEmbeddingService,
    IIndexStateService,
    IRetrievalService,
    IVectorIndexService,
)

logger = logging.getLogger("rag-backend.retrieval")


class RetrievalService(IRetrievalService):
    """Candidate context retrieval service querying the active ChromaDB vector index with candidate-quality filtering."""

    def __init__(
        self,
        embedding_service: Optional[IEmbeddingService] = None,
        vector_service: Optional[IVectorIndexService] = None,
        index_state_service: Optional[IIndexStateService] = None,
        config: Optional[RetrievalConfig] = None,
    ):
        self.embedding_service = embedding_service or get_embedding_service()
        self.vector_service = vector_service or get_vector_index_service()
        self.index_state_service = index_state_service or get_index_state_service()
        self.config = config or settings.rag.retrieval

    def retrieve(
        self,
        question: str,
        top_k: Optional[int] = None,
    ) -> RetrievalResponse:
        """Retrieve candidate context chunks from active indexed documents without making final answerability decisions."""
        if not question or not question.strip():
            raise ValueError("Question cannot be empty or whitespace only.")

        clean_question = question.strip()
        threshold = self.config.similarity_threshold
        active_state = self.index_state_service.get_state()
        active_doc_count = len(active_state.active_document_ids)

        # If no active documents in index, return empty candidate set
        if active_doc_count == 0:
            logger.info("Retrieval returned no candidates: active document set is empty.")
            return RetrievalResponse(
                question=clean_question,
                status="no_candidates",
                chunks=[],
                chunk_count=0,
                threshold=threshold,
                active_document_count=0,
            )

        # 1. Generate query embedding with BAAI/bge-small-en-v1.5
        try:
            query_vector = self.embedding_service.embed_text(clean_question)
        except Exception as e:
            logger.error("Failed to generate query embedding: %s", e)
            raise RuntimeError(f"Embedding generation failed for query: {str(e)}") from e

        # 2. Query candidate chunks from ChromaDB
        candidate_limit = max(self.config.candidate_k, (top_k or self.config.top_k))
        try:
            candidate_hits = self.vector_service.query_similarity(
                query_embedding=query_vector,
                top_k=candidate_limit,
            )
        except Exception as e:
            logger.error("Vector search failed during retrieval: %s", e)
            raise RuntimeError(f"Vector search failed: {str(e)}") from e

        # 3. Apply candidate-quality filter (similarity_score >= candidate threshold)
        filtered_hits = [
            hit for hit in candidate_hits
            if hit["similarity_score"] >= threshold
        ]

        # 4. Limit to requested top_k bounded by max_context_chunks
        target_k = min(top_k or self.config.top_k, self.config.max_context_chunks)
        selected_hits = filtered_hits[:target_k]

        if not selected_hits:
            logger.info(
                "Retrieval found no candidate chunks passing quality threshold %.2f",
                threshold,
            )
            return RetrievalResponse(
                question=clean_question,
                status="no_candidates",
                chunks=[],
                chunk_count=0,
                threshold=threshold,
                active_document_count=active_doc_count,
            )

        # Convert to RetrievalChunk schemas
        retrieval_chunks = [
            RetrievalChunk(
                chunk_id=hit["chunk_id"],
                document_id=hit["document_id"],
                title=hit["title"],
                source_type=hit["source_type"],
                content=hit["content"],
                similarity_score=hit["similarity_score"],
                metadata=hit["metadata"],
            )
            for hit in selected_hits
        ]

        logger.info(
            "Retrieval returned %d candidate chunk(s) for query: '%s'",
            len(retrieval_chunks),
            clean_question[:50],
        )

        return RetrievalResponse(
            question=clean_question,
            status="success",
            chunks=retrieval_chunks,
            chunk_count=len(retrieval_chunks),
            threshold=threshold,
            active_document_count=active_doc_count,
        )


_retrieval_service_instance: Optional[RetrievalService] = None


def get_retrieval_service() -> IRetrievalService:
    """Dependency provider for RetrievalService singleton."""
    global _retrieval_service_instance
    if _retrieval_service_instance is None:
        _retrieval_service_instance = RetrievalService()
    return _retrieval_service_instance
