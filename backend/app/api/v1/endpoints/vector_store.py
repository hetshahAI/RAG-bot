from fastapi import APIRouter, Depends, HTTPException, status

from app.models.schemas import VectorStoreClearResponse, VectorStoreInfoResponse
from app.services.chroma import get_vector_index_service
from app.services.interfaces import IVectorIndexService

router = APIRouter(prefix="/vector-store", tags=["Vector Store"])


@router.get(
    "/info",
    response_model=VectorStoreInfoResponse,
    summary="Vector Store Info",
    description="Retrieve safe status, point count, and persistence details of the local ChromaDB vector database.",
)
async def get_vector_store_info(
    vector_service: IVectorIndexService = Depends(get_vector_index_service),
) -> VectorStoreInfoResponse:
    """Return safe ChromaDB collection information."""
    info = vector_service.get_collection_info()
    return VectorStoreInfoResponse(
        provider=info["provider"],
        collection_name=info["collection_name"],
        collection_exists=info["collection_exists"],
        vector_dimension=info["vector_dimension"],
        point_count=info["point_count"],
        persistence_path=info["persistence_path"],
    )


@router.post(
    "/clear",
    response_model=VectorStoreClearResponse,
    summary="Clear Vector Store Collection",
    description="Truncate/reset the vector database collection. Does not delete raw uploaded documents from data/raw/.",
)
async def clear_vector_store(
    vector_service: IVectorIndexService = Depends(get_vector_index_service),
) -> VectorStoreClearResponse:
    """Clear vector index collection points."""
    try:
        info = vector_service.get_collection_info()
        col_name = info["collection_name"]
        vector_service.clear_index(col_name)
        return VectorStoreClearResponse(
            status="ok",
            message=f"ChromaDB collection '{col_name}' cleared successfully.",
            collection_name=col_name,
            point_count=0,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear vector store: {str(e)}",
        ) from e
