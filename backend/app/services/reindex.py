import logging
from typing import List, Optional

from app.core.config import settings
from app.models.schemas import ReindexResponse
from app.services.chroma import get_vector_index_service
from app.services.chunking import get_chunking_service
from app.services.embeddings import get_embedding_service
from app.services.index_state import get_index_state_service
from app.services.ingestion import get_ingestion_service
from app.services.interfaces import (
    IChunkingService,
    IEmbeddingService,
    IIndexStateService,
    IIngestionService,
    IVectorIndexService,
)

logger = logging.getLogger("rag-backend.reindex")


class ReindexService:
    """Orchestrator for the full reindexing pipeline: Chunk -> Embed -> Index -> Commit State."""

    def __init__(
        self,
        ingestion_service: Optional[IIngestionService] = None,
        chunking_service: Optional[IChunkingService] = None,
        embedding_service: Optional[IEmbeddingService] = None,
        vector_index_service: Optional[IVectorIndexService] = None,
        index_state_service: Optional[IIndexStateService] = None,
    ):
        self.ingestion_service = ingestion_service or get_ingestion_service()
        self.chunking_service = chunking_service or get_chunking_service()
        self.embedding_service = embedding_service or get_embedding_service()
        self.vector_index_service = vector_index_service or get_vector_index_service()
        self.index_state_service = index_state_service or get_index_state_service()

    def execute_reindex(self, document_ids: List[str]) -> ReindexResponse:
        """Execute atomic end-to-end reindex orchestration."""
        # Deduplicate document IDs while preserving order
        seen = set()
        deduped_ids = [d for d in document_ids if not (d in seen or seen.add(d))]

        if not deduped_ids:
            raise ValueError("document_ids must contain at least one valid document ID.")

        # Step 0: Validate existence of all requested documents
        found_docs, missing_ids = self.ingestion_service.get_documents_by_ids(deduped_ids)
        if missing_ids:
            raise LookupError(f"The following document ID(s) were not found: {', '.join(missing_ids)}")

        # Step 1: Chunk ONLY the selected documents
        try:
            chunks = self.chunking_service.chunk_documents(found_docs)
            logger.info("Generated %d chunk(s) across %d selected document(s)", len(chunks), len(found_docs))
        except Exception as e:
            logger.error("Chunking phase failed during reindex: %s", e)
            raise RuntimeError(f"Chunking phase failed: {str(e)}") from e

        # Step 2: Generate dense vector embeddings (contract)
        try:
            embeddings = self.embedding_service.embed_chunks(chunks)
            logger.info("Generated %d embedding(s)", len(embeddings))
        except Exception as e:
            logger.error("Embedding phase failed during reindex: %s", e)
            raise RuntimeError(f"Embedding phase failed: {str(e)}") from e

        # Step 3: Atomically replace active vector index in vector database (contract)
        collection_name = getattr(self.vector_index_service, "default_collection_name", settings.rag.vector_db.collection_name)
        try:
            self.vector_index_service.replace_index(
                collection_name=collection_name,
                chunks=chunks,
                embeddings=embeddings,
            )
            logger.info("Replaced vector index collection '%s' with %d item(s)", collection_name, len(chunks))
        except Exception as e:
            logger.error("Vector indexing phase failed during reindex: %s", e)
            raise RuntimeError(f"Vector indexing phase failed: {str(e)}") from e

        # Step 4: Commit active index state ONLY after upstream phases successfully complete
        try:
            new_state = self.index_state_service.set_active_documents(deduped_ids)
            logger.info("Committed active index state with document IDs: %s", deduped_ids)
        except Exception as e:
            logger.error("Failed to commit index state: %s", e)
            raise RuntimeError(f"Failed to commit index state: {str(e)}") from e

        return ReindexResponse(
            status="completed",
            indexing_version=new_state.indexing_version,
            selected_document_count=len(found_docs),
            chunk_count=len(chunks),
            embedding_count=len(embeddings),
            indexed_at=new_state.updated_at,
            document_ids=deduped_ids,
        )


def get_reindex_service() -> ReindexService:
    """Dependency provider for ReindexService."""
    return ReindexService()
