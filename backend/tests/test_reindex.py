import io
import json
from pathlib import Path
from typing import List

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas

from app.main import app
from app.models.schemas import Chunk, DocumentModel, DocumentPage
from app.services.chroma import ChromaVectorService, get_vector_index_service
from app.services.chunking import ChunkingService, get_chunking_service
from app.services.index_state import IndexStateService, get_index_state_service
from app.services.ingestion import IngestionService, get_ingestion_service
from app.services.interfaces import IVectorIndexService
from app.services.placeholders import EmbeddingServicePlaceholder
from app.services.reindex import ReindexService, get_reindex_service

client = TestClient(app)


@pytest.fixture
def isolated_env(tmp_path):
    """Fixture providing isolated data/raw and data/indexes directories."""
    raw_dir = tmp_path / "raw"
    indexes_dir = tmp_path / "indexes"
    chroma_dir = indexes_dir / "chroma"
    raw_dir.mkdir(parents=True, exist_ok=True)
    indexes_dir.mkdir(parents=True, exist_ok=True)
    chroma_dir.mkdir(parents=True, exist_ok=True)

    state_file = indexes_dir / "index_state.json"
    ingestion_service = IngestionService(raw_data_dir=raw_dir)
    state_service = IndexStateService(state_file_path=state_file)
    chunking_service = ChunkingService()
    embedding_service = EmbeddingServicePlaceholder()
    vector_index_service = ChromaVectorService(persist_directory=chroma_dir)
    reindex_service = ReindexService(
        ingestion_service=ingestion_service,
        chunking_service=chunking_service,
        embedding_service=embedding_service,
        vector_index_service=vector_index_service,
        index_state_service=state_service,
    )

    app.dependency_overrides[get_ingestion_service] = lambda: ingestion_service
    app.dependency_overrides[get_index_state_service] = lambda: state_service
    app.dependency_overrides[get_chunking_service] = lambda: chunking_service
    app.dependency_overrides[get_vector_index_service] = lambda: vector_index_service
    app.dependency_overrides[get_reindex_service] = lambda: reindex_service

    yield {
        "raw_dir": raw_dir,
        "indexes_dir": indexes_dir,
        "chroma_dir": chroma_dir,
        "state_file": state_file,
        "ingestion": ingestion_service,
        "state": state_service,
        "chunking": chunking_service,
        "embedding": embedding_service,
        "vector_index": vector_index_service,
        "reindex": reindex_service,
    }

    app.dependency_overrides.clear()


def generate_pdf_bytes(pages_text: List[str]) -> bytes:
    """Generate test PDF bytes."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    for idx, text in enumerate(pages_text):
        if idx > 0:
            c.showPage()
        c.setFont("Helvetica", 12)
        c.drawString(72, 720, text)
    c.save()
    buf.seek(0)
    return buf.getvalue()


def generate_image_bytes(text: str) -> bytes:
    """Generate test image bytes."""
    img = Image.new("RGB", (600, 150), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((40, 50), text, fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


# ============================================================================
# Documents Listing API Tests
# ============================================================================


def test_list_documents_empty(isolated_env):
    """Verify GET /api/v1/documents returns empty list when no files uploaded."""
    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 0
    assert data["active_count"] == 0
    assert data["documents"] == []


def test_list_documents_with_items(isolated_env):
    """Verify GET /api/v1/documents returns uploaded documents with is_active flag."""
    ingestion = isolated_env["ingestion"]
    doc1 = ingestion.create_and_store_document("First text doc", "doc1.txt", "txt")
    doc2 = ingestion.create_and_store_document("Second text doc", "doc2.txt", "txt")

    state_service = isolated_env["state"]
    state_service.set_active_documents([doc1.document_id])

    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 2
    assert data["active_count"] == 1

    doc_map = {d["document_id"]: d for d in data["documents"]}
    assert doc_map[doc1.document_id]["is_active"] is True
    assert doc_map[doc2.document_id]["is_active"] is False


# ============================================================================
# Reindex Preview API Tests
# ============================================================================


def test_reindex_preview_single_document(isolated_env):
    """Verify /reindex/preview generates chunks for a single selected document."""
    ingestion = isolated_env["ingestion"]
    long_content = "This is a detailed paragraph about building RAG pipelines with FastAPI.\n\n" * 10
    doc = ingestion.create_and_store_document(long_content, "architecture.txt", "txt")

    payload = {"document_ids": [doc.document_id]}
    response = client.post("/api/v1/reindex/preview", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["selected_document_count"] == 1
    assert data["total_chunk_count"] > 0
    assert "chunk_statistics" in data
    assert data["chunk_statistics"]["total_chunks"] == data["total_chunk_count"]
    assert len(data["sample_chunks"]) > 0
    assert data["sample_chunks"][0]["document_id"] == doc.document_id


def test_reindex_preview_multiple_documents(isolated_env):
    """Verify /reindex/preview handles multiple selected documents."""
    ingestion = isolated_env["ingestion"]
    doc1 = ingestion.create_and_store_document("Alpha doc content " * 10, "doc1.txt", "txt")
    doc2 = ingestion.create_and_store_document("Beta doc content " * 10, "doc2.txt", "txt")

    payload = {"document_ids": [doc1.document_id, doc2.document_id]}
    response = client.post("/api/v1/reindex/preview", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["selected_document_count"] == 2
    assert data["total_chunk_count"] >= 2
    assert len(data["source_documents"]) == 2


def test_reindex_preview_unknown_document_id(isolated_env):
    """Verify /reindex/preview returns HTTP 404 when an unknown document ID is requested."""
    payload = {"document_ids": ["doc_non_existent_12345"]}
    response = client.post("/api/v1/reindex/preview", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_unselected_documents_never_chunked(isolated_env):
    """Verify unselected documents present in raw storage are completely ignored."""
    ingestion = isolated_env["ingestion"]
    selected_doc = ingestion.create_and_store_document("Selected document text " * 5, "selected.txt", "txt")
    unselected_doc = ingestion.create_and_store_document("SECRET UNSELECTED CONTENT " * 5, "secret.txt", "txt")

    payload = {"document_ids": [selected_doc.document_id]}
    response = client.post("/api/v1/reindex/preview", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["selected_document_count"] == 1
    for chunk in data["sample_chunks"]:
        assert chunk["document_id"] == selected_doc.document_id
        assert "SECRET UNSELECTED CONTENT" not in chunk["content"]


def test_pdf_page_metadata_preservation_in_chunks(isolated_env):
    """Verify PDF multi-page chunks preserve page_number in metadata."""
    ingestion = isolated_env["ingestion"]
    pdf_bytes = generate_pdf_bytes([
        "Page 1: Architecture of RAG",
        "Page 2: Vector DB indexing",
    ])
    doc = ingestion.ingest_file("handbook.pdf", pdf_bytes)

    payload = {"document_ids": [doc.document_id]}
    response = client.post("/api/v1/reindex/preview", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["total_chunk_count"] == 2
    chunks = data["sample_chunks"]
    page_numbers = [c["metadata"]["page_number"] for c in chunks]
    assert page_numbers == [1, 2]
    assert chunks[0]["metadata"]["source_type"] == "pdf"
    assert chunks[0]["metadata"]["title"] == "handbook.pdf"


def test_image_ocr_metadata_preservation_in_chunks(isolated_env):
    """Verify image OCR chunks preserve image metadata (format, dimensions, engine)."""
    ingestion = isolated_env["ingestion"]
    img_bytes = generate_image_bytes("INVOICE NUMBER 1024")
    doc = ingestion.ingest_file("receipt.png", img_bytes)

    payload = {"document_ids": [doc.document_id]}
    response = client.post("/api/v1/reindex/preview", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["total_chunk_count"] > 0
    chunk = data["sample_chunks"][0]
    assert chunk["source_type"] == "image"
    assert chunk["metadata"]["format"] == "PNG"
    assert chunk["metadata"]["engine"] == "tesseract"
    assert "1024" in chunk["content"]


def test_deterministic_chunks(isolated_env):
    """Verify chunking produces identical chunk IDs, slices, and count across repeated runs."""
    chunking_service = isolated_env["chunking"]
    sample_text = (
        "FastAPI is a modern, fast web framework for building APIs with Python.\n\n"
        "Qdrant is a vector similarity search engine.\n\n"
        "BAAI/bge-small-en-v1.5 produces high-quality sentence embeddings.\n\n"
    ) * 5

    doc = DocumentModel(
        document_id="doc_fixed_test_100",
        title="deterministic.txt",
        source_type="txt",
        content=sample_text.strip(),
        character_count=len(sample_text.strip()),
    )

    run_1 = chunking_service.chunk_document(doc)
    run_2 = chunking_service.chunk_document(doc)

    assert len(run_1) == len(run_2)
    for c1, c2 in zip(run_1, run_2):
        assert c1.chunk_id == c2.chunk_id
        assert c1.content == c2.content
        assert c1.chunk_index == c2.chunk_index
        assert c1.character_count == c2.character_count
        assert c1.metadata == c2.metadata


def test_reindex_preview_does_not_modify_state(isolated_env):
    """Verify calling /reindex/preview does NOT modify active index state."""
    ingestion = isolated_env["ingestion"]
    state_service = isolated_env["state"]

    doc = ingestion.create_and_store_document("Document for preview only", "preview.txt", "txt")
    assert state_service.is_active(doc.document_id) is False

    response = client.post("/api/v1/reindex/preview", json={"document_ids": [doc.document_id]})
    assert response.status_code == 200

    # Ensure state was NOT altered
    assert state_service.is_active(doc.document_id) is False


# ============================================================================
# Reindex Execution API Tests (Step 1.7)
# ============================================================================


def test_reindex_valid_request(isolated_env):
    """Verify POST /api/v1/reindex orchestrates pipeline, replaces active index, and returns contract."""
    ingestion = isolated_env["ingestion"]
    state_service = isolated_env["state"]

    doc1 = ingestion.create_and_store_document("Alpha content for active index", "doc1.txt", "txt")
    doc2 = ingestion.create_and_store_document("Beta content for active index", "doc2.txt", "txt")

    payload = {"document_ids": [doc1.document_id, doc2.document_id]}
    response = client.post("/api/v1/reindex", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "completed"
    assert data["indexing_version"] == "v1"
    assert data["selected_document_count"] == 2
    assert data["chunk_count"] >= 2
    assert data["embedding_count"] == data["chunk_count"]
    assert "indexed_at" in data
    assert data["document_ids"] == [doc1.document_id, doc2.document_id]

    # Verify state was committed
    assert state_service.is_active(doc1.document_id) is True
    assert state_service.is_active(doc2.document_id) is True


def test_reindex_replaces_existing_active_index(isolated_env):
    """Verify reindexing replaces the previous active index set rather than appending."""
    ingestion = isolated_env["ingestion"]
    state_service = isolated_env["state"]

    doc1 = ingestion.create_and_store_document("Initial active document", "doc1.txt", "txt")
    doc2 = ingestion.create_and_store_document("New active document", "doc2.txt", "txt")

    # Initial reindex with doc1
    res1 = client.post("/api/v1/reindex", json={"document_ids": [doc1.document_id]})
    assert res1.status_code == 200
    assert state_service.is_active(doc1.document_id) is True
    assert state_service.is_active(doc2.document_id) is False

    # Second reindex with ONLY doc2
    res2 = client.post("/api/v1/reindex", json={"document_ids": [doc2.document_id]})
    assert res2.status_code == 200
    assert res2.json()["document_ids"] == [doc2.document_id]

    # Verify doc1 is NO LONGER active and doc2 IS active
    assert state_service.is_active(doc1.document_id) is False
    assert state_service.is_active(doc2.document_id) is True


def test_reindex_duplicate_document_ids(isolated_env):
    """Verify duplicate document IDs in request are safely deduplicated."""
    ingestion = isolated_env["ingestion"]
    doc = ingestion.create_and_store_document("Unique document text", "unique.txt", "txt")

    payload = {"document_ids": [doc.document_id, doc.document_id, doc.document_id]}
    response = client.post("/api/v1/reindex", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["selected_document_count"] == 1
    assert data["document_ids"] == [doc.document_id]


def test_reindex_empty_selection():
    """Verify empty document_ids list is rejected with HTTP 422."""
    payload = {"document_ids": []}
    response = client.post("/api/v1/reindex", json=payload)
    assert response.status_code == 422


def test_reindex_unknown_document(isolated_env):
    """Verify unknown document ID returns HTTP 404."""
    payload = {"document_ids": ["doc_unrecognized_abc123"]}
    response = client.post("/api/v1/reindex", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_reindex_atomic_failure_preserves_previous_state(isolated_env):
    """Verify that if vector indexing fails, previous active state is untouched."""
    ingestion = isolated_env["ingestion"]
    state_service = isolated_env["state"]

    doc1 = ingestion.create_and_store_document("Doc 1 original", "doc1.txt", "txt")
    doc2 = ingestion.create_and_store_document("Doc 2 target", "doc2.txt", "txt")

    # Set initial state with doc1
    state_service.set_active_documents([doc1.document_id])
    assert state_service.is_active(doc1.document_id) is True

    # Create a failing vector index service
    class FailingVectorIndexService(IVectorIndexService):
        def create_collection_if_not_exists(self, collection_name=None):
            pass

        def replace_index(self, collection_name: str, chunks: List[Chunk], embeddings: List[List[float]]) -> int:
            raise RuntimeError("Vector database connection timed out")

        def clear_index(self, collection_name=None) -> None:
            pass

        def collection_exists(self, collection_name=None) -> bool:
            return True

        def get_collection_info(self, collection_name=None):
            return {}

        def query_similarity(self, query_embedding, top_k=5, collection_name=None):
            return []

    failing_reindex_service = ReindexService(
        ingestion_service=isolated_env["ingestion"],
        chunking_service=isolated_env["chunking"],
        embedding_service=isolated_env["embedding"],
        vector_index_service=FailingVectorIndexService(),
        index_state_service=state_service,
    )
    app.dependency_overrides[get_reindex_service] = lambda: failing_reindex_service

    # Attempt reindex to doc2 (which will fail)
    response = client.post("/api/v1/reindex", json={"document_ids": [doc2.document_id]})
    assert response.status_code == 500
    assert "Vector database connection timed out" in response.json()["detail"]

    # Verify active state was NOT corrupted/replaced: doc1 is STILL active, doc2 is NOT
    assert state_service.is_active(doc1.document_id) is True
    assert state_service.is_active(doc2.document_id) is False


def test_clear_active_index_preserves_raw_files(isolated_env):
    """Verify POST /api/v1/reindex/clear clears active state without deleting raw files."""
    ingestion = isolated_env["ingestion"]
    state_service = isolated_env["state"]

    doc = ingestion.create_and_store_document("Important document", "doc.txt", "txt")
    state_service.set_active_documents([doc.document_id])

    assert state_service.is_active(doc.document_id) is True

    # Clear active selection
    response = client.post("/api/v1/reindex/clear")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["active_count"] == 0

    # Ensure state is cleared
    assert state_service.is_active(doc.document_id) is False

    # Ensure raw document STILL exists in raw storage
    raw_doc = ingestion.get_document(doc.document_id)
    assert raw_doc is not None
    assert raw_doc.title == "doc.txt"
