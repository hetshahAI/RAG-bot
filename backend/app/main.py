from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints.health import health_check
from app.api.v1.router import api_router
from app.core.config import settings
from app.models.schemas import HealthResponse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("rag-backend")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager."""
    logger.info("Starting up %s v%s", settings.app.name, settings.app.version)
    logger.info("Environment: %s", settings.app_env)
    logger.info("Embedding Model configured: %s", settings.rag.embedding.model_name)
    logger.info("Vector DB configured: %s", settings.rag.vector_db.provider)
    yield
    logger.info("Shutting down %s", settings.app.name)


def create_application() -> FastAPI:
    """FastAPI application factory."""
    application = FastAPI(
        title=settings.app.name,
        version=settings.app.version,
        description=settings.app.description,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Configure CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Root health check endpoint as required: GET /health
    application.add_api_route(
        "/health",
        health_check,
        methods=["GET"],
        response_model=HealthResponse,
        summary="Service Health Check",
        tags=["Health"],
    )

    # Include versioned API router (/api/v1)
    application.include_router(api_router, prefix=settings.app.api_prefix)

    @application.get("/", tags=["Root"], summary="Root Endpoint")
    async def root():
        return {
            "service": settings.app.name,
            "version": settings.app.version,
            "status": "online",
            "docs": "/docs",
            "health": "/health",
        }

    return application


app = create_application()
