import logging
from typing import Any, Dict, List, Optional

from app.core.config import EmbeddingConfig, settings
from app.models.schemas import Chunk
from app.services.interfaces import IEmbeddingService

logger = logging.getLogger("rag-backend.embeddings")


class EmbeddingService(IEmbeddingService):
    """Dense vector embedding service using sentence-transformers and BAAI/bge-small-en-v1.5."""

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        self.config = config or settings.rag.embedding
        self._model = None
        self._resolved_device: Optional[str] = None
        self.dimension: int = self.config.dimension

    def _get_device(self) -> str:
        """Resolve target compute device with automatic CUDA->CPU fallback."""
        if self._resolved_device is not None:
            return self._resolved_device

        target_device = (self.config.device or "cpu").lower()
        if target_device in ("cuda", "gpu"):
            try:
                import torch

                if torch.cuda.is_available():
                    self._resolved_device = "cuda"
                else:
                    logger.warning("CUDA requested but not available; automatically falling back to CPU.")
                    self._resolved_device = "cpu"
            except Exception as e:
                logger.warning("Error checking CUDA availability (%s); falling back to CPU.", e)
                self._resolved_device = "cpu"
        else:
            self._resolved_device = "cpu"

        return self._resolved_device

    def _load_model(self):
        """Lazy model loader ensuring model is loaded once on first inference."""
        if self._model is not None:
            return self._model

        logger.info(
            "Initializing SentenceTransformer model '%s' on device '%s' (lazy loading)...",
            self.config.model_name,
            self._get_device(),
        )

        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(
                model_name_or_path=self.config.model_name,
                device=self._get_device(),
            )
            logger.info("Successfully loaded embedding model '%s'", self.config.model_name)
            return self._model
        except Exception as e:
            logger.error("Failed to load embedding model '%s': %s", self.config.model_name, e)
            raise RuntimeError(f"Failed to initialize embedding model: {str(e)}") from e

    def embed_text(self, text: str) -> List[float]:
        """Generate normalized embedding vector for a single text."""
        if not text or not text.strip():
            raise ValueError("Text content cannot be empty or whitespace only.")
        results = self.embed_texts([text])
        return results[0]

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Batch generate normalized embedding vectors for multiple texts."""
        if not texts:
            raise ValueError("texts list cannot be empty.")

        cleaned_texts: List[str] = []
        for idx, t in enumerate(texts):
            if not t or not t.strip():
                raise ValueError(f"Text at index {idx} cannot be empty or whitespace only.")
            cleaned_texts.append(t.strip())

        model = self._load_model()
        try:
            embeddings = model.encode(
                cleaned_texts,
                batch_size=self.config.batch_size,
                normalize_embeddings=self.config.normalize_embeddings,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
            return embeddings.tolist()
        except Exception as e:
            logger.error("Error during embedding inference: %s", e)
            raise RuntimeError(f"Embedding inference failed: {str(e)}") from e

    def embed_chunks(self, chunks: List[Chunk]) -> List[List[float]]:
        """Extract text content from chunks and generate batch embeddings."""
        if not chunks:
            return []

        texts = [c.content for c in chunks]
        return self.embed_texts(texts)

    def get_dimension(self) -> int:
        """Return the embedding dimension (384 for BAAI/bge-small-en-v1.5)."""
        return self.dimension

    def get_model_info(self) -> Dict[str, Any]:
        """Return model metadata and active device configuration."""
        return {
            "model_name": self.config.model_name,
            "dimension": self.dimension,
            "device": self._get_device(),
            "normalize_embeddings": self.config.normalize_embeddings,
        }


_embedding_service_instance: Optional[EmbeddingService] = None


def get_embedding_service() -> IEmbeddingService:
    """Dependency provider for the embedding service singleton."""
    global _embedding_service_instance
    if _embedding_service_instance is None:
        _embedding_service_instance = EmbeddingService()
    return _embedding_service_instance
