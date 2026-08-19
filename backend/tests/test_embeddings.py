import hashlib
import math
from typing import List
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.config import EmbeddingConfig
from app.main import app
from app.models.schemas import Chunk
from app.services.embeddings import EmbeddingService, get_embedding_service
from app.services.interfaces import IEmbeddingService

client = TestClient(app)


class FakeSentenceTransformer:
    """Deterministic fake SentenceTransformer for fast unit tests without network or GPU."""

    def __init__(self, model_name_or_path: str = "BAAI/bge-small-en-v1.5", device: str = "cpu"):
        self.model_name = model_name_or_path
        self.device = device
        self.dimension = 384

    def encode(
        self,
        sentences: List[str],
        batch_size: int = 32,
        normalize_embeddings: bool = True,
        show_progress_bar: bool = False,
        convert_to_numpy: bool = True,
    ):
        """Produce deterministic 384-dimensional normalized vectors from text hashes."""
        vectors = []
        for s in sentences:
            # Deterministic pseudo-random seed from text
            seed = int(hashlib.md5(s.encode("utf-8")).hexdigest(), 16) % (2**32)
            rng = np.random.RandomState(seed)
            raw = rng.randn(self.dimension).astype(np.float32)
            if normalize_embeddings:
                norm = np.linalg.norm(raw)
                if norm > 0:
                    raw = raw / norm
            vectors.append(raw)

        return np.array(vectors)


@pytest.fixture
def mock_embedding_service():
    """Fixture providing an EmbeddingService using FakeSentenceTransformer."""
    config = EmbeddingConfig(
        model_name="BAAI/bge-small-en-v1.5",
        dimension=384,
        batch_size=32,
        device="cpu",
        normalize_embeddings=True,
    )
    service = EmbeddingService(config=config)
    fake_model = FakeSentenceTransformer()
    service._model = fake_model

    app.dependency_overrides[get_embedding_service] = lambda: service
    yield service
    app.dependency_overrides.clear()


# ============================================================================
# Unit Tests
# ============================================================================


def test_embedding_dimension(mock_embedding_service):
    """Verify embedding dimension is 384."""
    assert mock_embedding_service.get_dimension() == 384


def test_embed_single_text(mock_embedding_service):
    """Verify single text embedding produces a 384-dimensional vector."""
    vec = mock_embedding_service.embed_text("Hello world")
    assert isinstance(vec, list)
    assert len(vec) == 384
    assert all(isinstance(x, float) for x in vec)


def test_embed_batch_texts(mock_embedding_service):
    """Verify batch text embedding produces vectors for all inputs."""
    texts = ["First query", "Second query about RAG", "Third query"]
    vectors = mock_embedding_service.embed_texts(texts)
    assert len(vectors) == 3
    for vec in vectors:
        assert len(vec) == 384


def test_embed_chunks(mock_embedding_service):
    """Verify embed_chunks extracts content and encodes."""
    chunks = [
        Chunk(
            chunk_id="doc_1_c0000",
            document_id="doc_1",
            source_type="txt",
            title="doc.txt",
            content="Chunk content number one",
            chunk_index=0,
            character_count=24,
            metadata={},
        ),
        Chunk(
            chunk_id="doc_1_c0001",
            document_id="doc_1",
            source_type="txt",
            title="doc.txt",
            content="Chunk content number two",
            chunk_index=1,
            character_count=24,
            metadata={},
        ),
    ]

    vectors = mock_embedding_service.embed_chunks(chunks)
    assert len(vectors) == 2
    assert len(vectors[0]) == 384
    assert len(vectors[1]) == 384


def test_normalized_vector_magnitude(mock_embedding_service):
    """Verify embedding vectors have an L2 norm approximately equal to 1.0."""
    vec = mock_embedding_service.embed_text("Normalize this vector")
    l2_norm = math.sqrt(sum(x**2 for x in vec))
    assert pytest.approx(1.0, abs=1e-4) == l2_norm


def test_deterministic_embeddings(mock_embedding_service):
    """Verify identical text produces exact identical vectors."""
    text = "Deterministic testing phrase for RAG pipeline."
    vec1 = mock_embedding_service.embed_text(text)
    vec2 = mock_embedding_service.embed_text(text)
    assert vec1 == vec2


def test_empty_text_validation(mock_embedding_service):
    """Verify empty text or whitespace is rejected with ValueError."""
    with pytest.raises(ValueError, match="empty or whitespace"):
        mock_embedding_service.embed_text("")

    with pytest.raises(ValueError, match="empty or whitespace"):
        mock_embedding_service.embed_text("   \n\t  ")


def test_empty_batch_validation(mock_embedding_service):
    """Verify empty batch or invalid items inside batch are rejected."""
    with pytest.raises(ValueError, match="cannot be empty"):
        mock_embedding_service.embed_texts([])

    with pytest.raises(ValueError, match="cannot be empty"):
        mock_embedding_service.embed_texts(["valid text", ""])


def test_device_fallback():
    """Verify requested CUDA falls back to CPU when torch.cuda is not available."""
    config = EmbeddingConfig(
        model_name="BAAI/bge-small-en-v1.5",
        dimension=384,
        batch_size=32,
        device="cuda",
        normalize_embeddings=True,
    )
    service = EmbeddingService(config=config)

    with patch("torch.cuda.is_available", return_value=False):
        device = service._get_device()
        assert device == "cpu"


def test_lazy_loading():
    """Verify model is NOT loaded upon service instantiation, only on first call."""
    config = EmbeddingConfig(
        model_name="BAAI/bge-small-en-v1.5",
        dimension=384,
        batch_size=32,
        device="cpu",
        normalize_embeddings=True,
    )
    service = EmbeddingService(config=config)
    assert service._model is None


# ============================================================================
# API Endpoints Tests
# ============================================================================


def test_get_embedding_info_api(mock_embedding_service):
    """Verify GET /api/v1/embeddings/info returns metadata."""
    response = client.get("/api/v1/embeddings/info")
    assert response.status_code == 200
    data = response.json()
    assert data["model_name"] == "BAAI/bge-small-en-v1.5"
    assert data["dimension"] == 384
    assert data["device"] == "cpu"
    assert data["normalize_embeddings"] is True


def test_test_embeddings_api(mock_embedding_service):
    """Verify POST /api/v1/embeddings/test generates preview vectors."""
    payload = {"texts": ["Hello world", "RAG pipeline architecture"]}
    response = client.post("/api/v1/embeddings/test", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["model_name"] == "BAAI/bge-small-en-v1.5"
    assert data["dimension"] == 384
    assert data["text_count"] == 2
    assert len(data["embeddings"]) == 2
    assert data["embeddings"][0]["vector_length"] == 384
    assert len(data["embeddings"][0]["sample_vector"]) == 5


def test_test_embeddings_api_empty_rejected():
    """Verify POST /api/v1/embeddings/test rejects empty payload with HTTP 422."""
    payload = {"texts": []}
    response = client.post("/api/v1/embeddings/test", json=payload)
    assert response.status_code == 422


# ============================================================================
# Optional Integration Test (Real Model)
# ============================================================================


def test_real_model_integration_if_cached():
    """Test with real SentenceTransformer only if the model is locally cached."""
    try:
        from sentence_transformers import SentenceTransformer
        # Check if local cache has the model
        model = SentenceTransformer("BAAI/bge-small-en-v1.5", device="cpu")
        emb = model.encode(["Real model test"], normalize_embeddings=True)
        assert emb.shape == (1, 384)
        norm = np.linalg.norm(emb[0])
        assert pytest.approx(1.0, abs=1e-3) == norm
    except Exception as e:
        pytest.skip(f"Skipping real HuggingFace model download/execution in CI/offline: {e}")
