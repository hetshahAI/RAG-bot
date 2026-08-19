from fastapi import APIRouter, Depends, HTTPException, status

from app.models.schemas import RetrievalRequest, RetrievalResponse
from app.services.interfaces import IRetrievalService
from app.services.retrieval import get_retrieval_service

router = APIRouter(prefix="/retrieval", tags=["Retrieval"])


@router.post(
    "/search",
    response_model=RetrievalResponse,
    summary="Strict Knowledge-Base Retrieval",
    description="Retrieve grounded evidence chunks matching the question strictly from the active indexed documents in ChromaDB.",
)
async def search_knowledge_base(
    payload: RetrievalRequest,
    retrieval_service: IRetrievalService = Depends(get_retrieval_service),
) -> RetrievalResponse:
    """Execute strict semantic similarity retrieval against active knowledge base."""
    try:
        return retrieval_service.retrieve(
            question=payload.question,
            top_k=payload.top_k,
        )
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
