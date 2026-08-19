import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.models.schemas import Chunk
from app.services.interfaces import IEmbeddingService, IVectorIndexService

logger = logging.getLogger("rag-backend.placeholders")


class EmbeddingServicePlaceholder(IEmbeddingService):
    """Placeholder service representing future dense vector embedding generation."""

    def __init__(self, dimension: int = 384):
        self.dimension = dimension or settings.rag.embedding.dimension

    def embed_text(self, text: str) -> List[float]:
        """Placeholder single text embedding."""
        if not text or not text.strip():
            raise ValueError("Text cannot be empty or whitespace only.")
        return [0.0] * self.dimension

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Placeholder batch text embedding."""
        if not texts:
            raise ValueError("texts list cannot be empty.")
        for t in texts:
            if not t or not t.strip():
                raise ValueError("Text in batch cannot be empty or whitespace only.")
        return [[0.0] * self.dimension for _ in texts]

    def embed_chunks(self, chunks: List[Chunk]) -> List[List[float]]:
        """Placeholder embedding contract returning simulated vectors."""
        logger.info(
            "Embedding contract invoked for %d chunk(s) with model %s (dim=%d)",
            len(chunks),
            settings.rag.embedding.model_name,
            self.dimension,
        )
        return [[0.0] * self.dimension for _ in chunks]

    def get_dimension(self) -> int:
        return self.dimension

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "model_name": settings.rag.embedding.model_name,
            "dimension": self.dimension,
            "device": settings.rag.embedding.device,
            "normalize_embeddings": settings.rag.embedding.normalize_embeddings,
        }


class VectorIndexServicePlaceholder(IVectorIndexService):
    """Placeholder service representing future vector database replacement."""

    def create_collection_if_not_exists(self, collection_name: Optional[str] = None) -> Any:
        return None

    def replace_index(
        self,
        collection_name: str,
        chunks: List[Chunk],
        embeddings: List[List[float]],
    ) -> int:
        """Placeholder index replacement contract."""
        logger.info(
            "Vector index replacement contract invoked for collection '%s' with %d item(s)",
            collection_name,
            len(chunks),
        )
        return len(chunks)

    def clear_index(self, collection_name: Optional[str] = None) -> None:
        """Placeholder clear index contract."""
        logger.info("Vector index clear contract invoked for collection '%s'", collection_name)

    def collection_exists(self, collection_name: Optional[str] = None) -> bool:
        return True

    def get_collection_info(self, collection_name: Optional[str] = None) -> Dict[str, Any]:
        return {
            "provider": "placeholder",
            "collection_name": collection_name or settings.rag.vector_db.collection_name,
            "collection_exists": True,
            "vector_dimension": 384,
            "point_count": 0,
            "persistence_path": "placeholder",
        }

    def query_similarity(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        collection_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return []
