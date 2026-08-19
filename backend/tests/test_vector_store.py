import json
from pathlib import Path
from typing import List

import pytest
from fastapi.testclient import TestClient

from app.core.config import VectorDBConfig
from app.main import app
from app.models.schemas import Chunk, DocumentModel
from app.services.chroma import ChromaVectorService, get_vector_index_service, sanitize_metadata_for_chroma
from app.services.chunking import ChunkingService
from app.services.embeddings import EmbeddingService
from app.services.index_state import IndexStateService
from app.services.ingestion import IngestionService
from app.services.reindex import ReindexService

client = TestClient(app)


@pytest.fixture
def temp_chroma_service(tmp_path):
    """Fixture providing an isolated ChromaVectorService in a temporary directory."""
    persist_dir = tmp_path / "indexes" / "chroma"
    config = VectorDBConfig(
        provider="chromadb",
        collection_name="test_rag_documents",
        persist_directory=str(persist_dir),
        distance_metric="cosine",
        batch_size=50,
    )
    service = ChromaVectorService(config=config, persist_directory=persist_dir)

    app.dependency_overrides[get_vector_index_service] = lambda: service
    yield service
    app.dependency_overrides.clear()


def make_dummy_vector(dim: int = 384, value: float = 0.05) -> List[float]:
    """Helper to generate dummy 384-dimensional vector."""
    return [value] * dim


def make_sample_chunk(
    chunk_id: str,
    doc_id: str = "doc_test_1",
    content: str = "Sample chunk content for testing",
    index: int = 0,
    metadata: dict = None,
) -> Chunk:
    """Helper to generate a test Chunk."""
    return Chunk(
        chunk_id=chunk_id,
        document_id=doc_id,
        source_type="txt",
        title="test_document.txt",
        content=content,
        chunk_index=index,
        character_count=len(content),
        metadata=metadata or {"author": "AI", "tags": ["rag", "fastapi"]},
    )


# ============================================================================
# Unit Tests for ChromaVectorService
# ============================================================================


def test_chroma_initialization(temp_chroma_service):
    """Verify Chroma initializes with correct persistence path and collection configuration."""
    assert temp_chroma_service.persist_directory.exists()
    assert temp_chroma_service.default_collection_name == "test_rag_documents"
    assert temp_chroma_service.dimension == 384


def test_collection_creation_and_exists(temp_chroma_service):
    """Verify create_collection_if_not_exists creates collection and collection_exists reports true."""
    assert temp_chroma_service.collection_exists() is False

    col = temp_chroma_service.create_collection_if_not_exists()
    assert col is not None
    assert temp_chroma_service.collection_exists() is True


def test_get_collection_info(temp_chroma_service):
    """Verify get_collection_info returns provider, point_count, and persistence details."""
    info = temp_chroma_service.get_collection_info()
    assert info["provider"] == "chromadb"
    assert info["collection_name"] == "test_rag_documents"
    assert info["collection_exists"] is False
    assert info["point_count"] == 0
    assert info["vector_dimension"] == 384
    assert str(temp_chroma_service.persist_directory) in info["persistence_path"]


def test_sanitize_metadata():
    """Verify metadata is sanitized into Chroma-compatible primitives."""
    raw = {
        "author": "Alice",
        "score": 42,
        "ratio": 3.14,
        "is_active": True,
        "empty_field": None,
        "tags": ["rag", "chroma"],
        "nested": {"key": "val"},
    }
    sanitized = sanitize_metadata_for_chroma(raw)

    assert sanitized["author"] == "Alice"
    assert sanitized["score"] == 42
    assert sanitized["ratio"] == 3.14
    assert sanitized["is_active"] is True
    assert "empty_field" not in sanitized
    assert json.loads(sanitized["tags"]) == ["rag", "chroma"]
    assert json.loads(sanitized["nested"]) == {"key": "val"}


def test_vector_insertion_and_point_count(temp_chroma_service):
    """Verify replacing index with valid chunks/embeddings inserts points."""
    chunks = [
        make_sample_chunk("c1", "doc1", "First chunk content", 0),
        make_sample_chunk("c2", "doc1", "Second chunk content", 1),
    ]
    embeddings = [make_dummy_vector(384, 0.1), make_dummy_vector(384, 0.2)]

    inserted = temp_chroma_service.replace_index("test_rag_documents", chunks, embeddings)
    assert inserted == 2

    info = temp_chroma_service.get_collection_info()
    assert info["collection_exists"] is True
    assert info["point_count"] == 2


def test_replacement_semantics(temp_chroma_service):
    """Verify replace_index replaces previous index rather than appending."""
    # First insertion: doc1 (2 chunks)
    chunks_v1 = [
        make_sample_chunk("c1", "doc1", "Chunk 1"),
        make_sample_chunk("c2", "doc1", "Chunk 2"),
    ]
    embs_v1 = [make_dummy_vector(384), make_dummy_vector(384)]
    temp_chroma_service.replace_index("test_rag_documents", chunks_v1, embs_v1)
    assert temp_chroma_service.get_collection_info()["point_count"] == 2

    # Second insertion: doc2 (1 chunk only)
    chunks_v2 = [make_sample_chunk("c3", "doc2", "Chunk 3")]
    embs_v2 = [make_dummy_vector(384)]
    temp_chroma_service.replace_index("test_rag_documents", chunks_v2, embs_v2)

    # Must be 1, NOT 3 (append is strictly forbidden)
    info = temp_chroma_service.get_collection_info()
    assert info["point_count"] == 1


def test_clear_index(temp_chroma_service):
    """Verify clear_index truncates the collection points."""
    chunks = [make_sample_chunk("c1", "doc1", "Chunk 1")]
    embs = [make_dummy_vector(384)]
    temp_chroma_service.replace_index("test_rag_documents", chunks, embs)
    assert temp_chroma_service.get_collection_info()["point_count"] == 1

    temp_chroma_service.clear_index("test_rag_documents")
    assert temp_chroma_service.get_collection_info()["point_count"] == 0


def test_validation_mismatch_count(temp_chroma_service):
    """Verify ValueError when chunk count != embeddings count."""
    chunks = [make_sample_chunk("c1")]
    embs = [make_dummy_vector(384), make_dummy_vector(384)]

    with pytest.raises(ValueError, match="Mismatch"):
        temp_chroma_service.replace_index("test_rag_documents", chunks, embs)


def test_validation_invalid_dimension(temp_chroma_service):
    """Verify ValueError when embedding dimension is not 384."""
    chunks = [make_sample_chunk("c1")]
    wrong_dim_embs = [make_dummy_vector(128)]  # wrong dimension

    with pytest.raises(ValueError, match="invalid dimension 128"):
        temp_chroma_service.replace_index("test_rag_documents", chunks, wrong_dim_embs)


def test_validation_empty_chunk_content(temp_chroma_service):
    """Verify ValueError when a chunk has empty content."""
    chunks = [make_sample_chunk("c1", content="   \n\t ")]
    embs = [make_dummy_vector(384)]

    with pytest.raises(ValueError, match="empty content"):
        temp_chroma_service.replace_index("test_rag_documents", chunks, embs)


def test_validation_duplicate_chunk_ids(temp_chroma_service):
    """Verify ValueError when duplicate chunk IDs are passed."""
    chunks = [
        make_sample_chunk("c1", content="First copy"),
        make_sample_chunk("c1", content="Duplicate copy with same ID"),
    ]
    embs = [make_dummy_vector(384), make_dummy_vector(384)]

    with pytest.raises(ValueError, match="Duplicate chunk ID"):
        temp_chroma_service.replace_index("test_rag_documents", chunks, embs)


def test_empty_chunks_replacement(temp_chroma_service):
    """Verify replacing with 0 chunks cleanly creates an empty collection."""
    inserted = temp_chroma_service.replace_index("test_rag_documents", [], [])
    assert inserted == 0
    assert temp_chroma_service.get_collection_info()["point_count"] == 0


# ============================================================================
# API Endpoints Tests
# ============================================================================


def test_get_vector_store_info_api(temp_chroma_service):
    """Verify GET /api/v1/vector-store/info returns collection status."""
    response = client.get("/api/v1/vector-store/info")
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "chromadb"
    assert data["collection_name"] == "test_rag_documents"
    assert data["vector_dimension"] == 384
    assert data["point_count"] == 0


def test_clear_vector_store_api(temp_chroma_service):
    """Verify POST /api/v1/vector-store/clear empties the collection."""
    # Seed a point
    chunks = [make_sample_chunk("c1")]
    embs = [make_dummy_vector(384)]
    temp_chroma_service.replace_index("test_rag_documents", chunks, embs)
    assert temp_chroma_service.get_collection_info()["point_count"] == 1

    response = client.post("/api/v1/vector-store/clear")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["point_count"] == 0
    assert temp_chroma_service.get_collection_info()["point_count"] == 0


# ============================================================================
# End-to-End Integration Test
# ============================================================================


def test_end_to_end_document_to_chroma(tmp_path):
    """Small end-to-end integration test: Document -> Chunk -> BGE Embeddings -> ChromaDB."""
    raw_dir = tmp_path / "raw"
    indexes_dir = tmp_path / "indexes"
    chroma_dir = indexes_dir / "chroma"
    raw_dir.mkdir(parents=True, exist_ok=True)
    chroma_dir.mkdir(parents=True, exist_ok=True)

    state_file = indexes_dir / "index_state.json"
    ingestion_service = IngestionService(raw_data_dir=raw_dir)
    state_service = IndexStateService(state_file_path=state_file)
    chunking_service = ChunkingService()
    embedding_service = EmbeddingService()
    vector_service = ChromaVectorService(persist_directory=chroma_dir)

    reindex_service = ReindexService(
        ingestion_service=ingestion_service,
        chunking_service=chunking_service,
        embedding_service=embedding_service,
        vector_index_service=vector_service,
        index_state_service=state_service,
    )

    # 1. Ingest raw document
    doc = ingestion_service.create_and_store_document(
        content="ChromaDB is a local, AI-native open-source vector database designed for developer productivity.\n\n"
                "BAAI/bge-small-en-v1.5 produces high-quality sentence embeddings for similarity search.",
        title="chroma_guide.txt",
        source_type="txt",
    )

    # 2. Execute full reindexing pipeline
    reindex_result = reindex_service.execute_reindex([doc.document_id])
    assert reindex_result.status == "completed"
    assert reindex_result.selected_document_count == 1
    assert reindex_result.chunk_count >= 1
    assert reindex_result.embedding_count == reindex_result.chunk_count

    # 3. Verify ChromaDB contains the indexed points
    info = vector_service.get_collection_info()
    assert info["collection_exists"] is True
    assert info["point_count"] == reindex_result.chunk_count

    # 4. Verify index state
    assert state_service.is_active(doc.document_id) is True
