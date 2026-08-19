from fastapi import APIRouter, Depends, HTTPException, status

from app.models.schemas import (
    EmbeddingInfoResponse,
    EmbeddingItemPreview,
    EmbeddingTestRequest,
    EmbeddingTestResponse,
)
from app.services.embeddings import get_embedding_service
from app.services.interfaces import IEmbeddingService

router = APIRouter(prefix="/embeddings", tags=["Embeddings"])


@router.get(
    "/info",
    response_model=EmbeddingInfoResponse,
    summary="Embedding Model Info",
    description="Retrieve metadata and configuration of the active embedding model.",
)
async def get_embedding_info(
    embedding_service: IEmbeddingService = Depends(get_embedding_service),
) -> EmbeddingInfoResponse:
    """Return embedding model information."""
    info = embedding_service.get_model_info()
    return EmbeddingInfoResponse(
        model_name=info["model_name"],
        dimension=info["dimension"],
        device=info["device"],
        normalize_embeddings=info["normalize_embeddings"],
    )


@router.post(
    "/test",
    response_model=EmbeddingTestResponse,
    summary="Test Embedding Generation",
    description="Generate sample embeddings for provided texts to verify model functionality and vector dimensions.",
)
async def test_embeddings(
    payload: EmbeddingTestRequest,
    embedding_service: IEmbeddingService = Depends(get_embedding_service),
) -> EmbeddingTestResponse:
    """Test embedding generation on provided texts."""
    try:
        vectors = embedding_service.embed_texts(payload.texts)
        info = embedding_service.get_model_info()

        items = [
            EmbeddingItemPreview(
                index=idx,
                text_preview=text[:80] + ("..." if len(text) > 80 else ""),
                character_count=len(text),
                vector_length=len(vec),
                sample_vector=[round(x, 6) for x in vec[:5]],
                vector=vec,
            )
            for idx, (text, vec) in enumerate(zip(payload.texts, vectors))
        ]

        return EmbeddingTestResponse(
            model_name=info["model_name"],
            dimension=info["dimension"],
            text_count=len(payload.texts),
            device=info["device"],
            normalize_embeddings=info["normalize_embeddings"],
            embeddings=items,
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
