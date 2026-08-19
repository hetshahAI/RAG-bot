from fastapi import APIRouter, Depends

from app.models.schemas import DocumentListResponse, DocumentSummary
from app.services.index_state import IndexStateService, get_index_state_service
from app.services.ingestion import IngestionService, get_ingestion_service

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List Uploaded Documents",
    description="Retrieve all raw documents stored in data/raw/ with active indexing status.",
)
async def list_documents(
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    state_service: IndexStateService = Depends(get_index_state_service),
) -> DocumentListResponse:
    """List all uploaded documents."""
    raw_docs = ingestion_service.list_documents()
    active_ids = set(state_service.get_state().active_document_ids)

    summaries = [
        DocumentSummary(
            document_id=doc.document_id,
            title=doc.title,
            source_type=doc.source_type,
            character_count=doc.character_count,
            page_count=doc.page_count,
            is_active=(doc.document_id in active_ids),
            created_at=doc.created_at,
        )
        for doc in raw_docs
    ]

    active_count = sum(1 for s in summaries if s.is_active)

    return DocumentListResponse(
        total_count=len(summaries),
        active_count=active_count,
        documents=summaries,
    )
