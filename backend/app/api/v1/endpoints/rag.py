from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.models.schemas import (
    RAGAskRequest,
    RAGAskResponse,
    RAGExecutionTrace,
)
from app.services.interfaces import IRAGService
from app.services.rag import get_rag_service

router = APIRouter(prefix="/rag", tags=["RAG QA"])


@router.post(
    "/ask",
    response_model=RAGAskResponse,
    summary="Strict Grounded Question Answering",
    description="Answer questions with strict knowledge-base grounding, evidence gating, and deterministic abstention.",
)
async def ask_rag(
    payload: RAGAskRequest,
    rag_service: IRAGService = Depends(get_rag_service),
) -> RAGAskResponse:
    """Execute strict grounded RAG QA pipeline."""
    try:
        return rag_service.ask(
            question=payload.question,
            top_k=payload.top_k,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG QA pipeline failure: {str(e)}",
        ) from e


@router.get(
    "/runs/{run_id}",
    response_model=RAGExecutionTrace,
    summary="Get RAG Execution Trace",
    description="Retrieve the sequential lifecycle trace and timing metrics for a specific RAG execution run.",
)
async def get_rag_run_trace(
    run_id: str = Path(..., description="Unique run identifier"),
    rag_service: IRAGService = Depends(get_rag_service),
) -> RAGExecutionTrace:
    """Retrieve execution trace for a given run ID."""
    trace = rag_service.get_run_trace(run_id)
    if trace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution trace for run_id '{run_id}' not found.",
        )
    return trace
