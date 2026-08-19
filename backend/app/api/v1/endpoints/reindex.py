from fastapi import APIRouter, Depends, HTTPException, status

from app.models.schemas import (
    DocumentSummary,
    ReindexPreviewRequest,
    ReindexPreviewResponse,
    ReindexRequest,
    ReindexResponse,
)
from app.services.chunking import ChunkingService, get_chunking_service
from app.services.index_state import IndexStateService, get_index_state_service
from app.services.ingestion import IngestionService, get_ingestion_service
from app.services.reindex import ReindexService, get_reindex_service

router = APIRouter(prefix="/reindex", tags=["Indexing & Selection"])


@router.post(
    "",
    response_model=ReindexResponse,
    summary="Execute Reindexing",
    description="Orchestrate full reindexing for selected documents (Chunk -> Embed -> Replace Vector Index -> Update State).",
)
async def execute_reindex(
    payload: ReindexRequest,
    reindex_service: ReindexService = Depends(get_reindex_service),
) -> ReindexResponse:
    """Execute reindexing for selected documents."""
    try:
        return reindex_service.execute_reindex(payload.document_ids)
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@router.post(
    "/preview",
    response_model=ReindexPreviewResponse,
    summary="Preview Reindexing and Chunking",
    description="Preview deterministic chunking and statistics for explicitly selected documents without modifying embeddings or Qdrant.",
)
async def preview_reindex(
    payload: ReindexPreviewRequest,
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    chunking_service: ChunkingService = Depends(get_chunking_service),
    state_service: IndexStateService = Depends(get_index_state_service),
) -> ReindexPreviewResponse:
    """Preview chunk generation for selected documents."""
    found_docs, missing_ids = ingestion_service.get_documents_by_ids(payload.document_ids)

    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"The following document ID(s) were not found: {', '.join(missing_ids)}",
        )

    if not found_docs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid documents selected for preview.",
        )

    # Chunk ONLY the selected documents
    chunks = chunking_service.chunk_documents(found_docs)
    stats = chunking_service.compute_statistics(chunks)

    active_ids = set(state_service.get_state().active_document_ids)
    source_summaries = [
        DocumentSummary(
            document_id=doc.document_id,
            title=doc.title,
            source_type=doc.source_type,
            character_count=doc.character_count,
            page_count=doc.page_count,
            is_active=(doc.document_id in active_ids),
            created_at=doc.created_at,
        )
        for doc in found_docs
    ]

    return ReindexPreviewResponse(
        selected_document_count=len(found_docs),
        total_chunk_count=len(chunks),
        chunk_statistics=stats,
        sample_chunks=chunks[:10],
        source_documents=source_summaries,
    )


@router.post(
    "/clear",
    summary="Clear Active Index Selection",
    description="Clear active document selection in index state without deleting raw uploaded documents.",
)
async def clear_active_index(
    state_service: IndexStateService = Depends(get_index_state_service),
):
    """Clear active indexed document set."""
    state_service.clear_active_documents()
    return {
        "status": "ok",
        "message": "Active index set cleared successfully.",
        "active_count": 0,
    }
