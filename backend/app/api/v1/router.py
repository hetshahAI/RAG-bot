from fastapi import APIRouter
from app.api.v1.endpoints import (
    documents,
    embeddings,
    health,
    ingest,
    rag,
    reindex,
    retrieval,
    vector_store,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(ingest.router)
api_router.include_router(documents.router)
api_router.include_router(reindex.router)
api_router.include_router(embeddings.router)
api_router.include_router(vector_store.router)
api_router.include_router(retrieval.router)
api_router.include_router(rag.router)
