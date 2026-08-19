from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)

from app.models.schemas import (
    DocumentIngestResponse,
    TextIngestRequest,
)
from app.services.ingestion import IngestionService, get_ingestion_service

router = APIRouter(prefix="/ingest", tags=["Ingestion"])


@router.post(
    "/text",
    response_model=DocumentIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest Plain Text",
    description="Normalize, create, and persist a raw text document for the RAG pipeline.",
)
async def ingest_text(
    payload: TextIngestRequest,
    service: IngestionService = Depends(get_ingestion_service),
) -> DocumentIngestResponse:
    """Ingest plain text endpoint."""
    try:
        document = service.ingest_text(payload)
        return service.to_response(document)
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
    "/file",
    response_model=DocumentIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest Document or Image File",
    description="Upload, validate, extract, normalize, and persist a .txt, .pdf, or image (.png, .jpg, .jpeg, .webp) file as a raw document.",
)
async def ingest_file(
    file: UploadFile = File(..., description="The document or image file to upload and ingest"),
    service: IngestionService = Depends(get_ingestion_service),
) -> DocumentIngestResponse:
    """Ingest uploaded file endpoint."""
    try:
        content_bytes = await file.read()
        document = service.ingest_file(filename=file.filename, file_bytes=content_bytes)
        return service.to_response(document)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
