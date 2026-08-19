from fastapi import APIRouter
from app.models.schemas import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check if the backend service is operational.",
    tags=["Health"],
)
async def health_check() -> HealthResponse:
    """Return health status of the RAG backend service."""
    return HealthResponse(status="ok", service="rag-backend")
