import pytest
from fastapi.testclient import TestClient

from app.core.config import RetrievalConfig, VectorDBConfig, settings
from app.main import app
from app.models.schemas import Chunk
from app.services.chroma import ChromaVectorService, get_vector_index_service
from app.services.chunking import ChunkingService, get_chunking_service
from app.services.embeddings import EmbeddingService, get_embedding_service
from app.services.index_state import IndexStateService, get_index_state_service
from app.services.ingestion import IngestionService, get_ingestion_service
from app.services.reindex import ReindexService, get_reindex_service
from app.services.retrieval import RetrievalService, get_retrieval_service

client = TestClient(app)


@pytest.fixture
def retrieval_env(tmp_path):
    """Fixture providing isolated services and storage for retrieval testing."""
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
    embedding_service = EmbeddingService()

    vector_config = VectorDBConfig(
        provider="chromadb",
        collection_name="test_retrieval_collection",
        persist_directory=str(chroma_dir),
        distance_metric="cosine",
        batch_size=50,
    )
    vector_service = ChromaVectorService(config=vector_config, persist_directory=chroma_dir)

    retrieval_config = RetrievalConfig(
        top_k=5,
        candidate_k=10,
        similarity_threshold=0.50,
        min_relevant_chunks=1,
        max_context_chunks=10,
    )
    retrieval_service = RetrievalService(
        embedding_service=embedding_service,
        vector_service=vector_service,
        index_state_service=state_service,
        config=retrieval_config,
    )

    reindex_service = ReindexService(
        ingestion_service=ingestion_service,
        chunking_service=chunking_service,
        embedding_service=embedding_service,
        vector_index_service=vector_service,
        index_state_service=state_service,
    )

    app.dependency_overrides[get_ingestion_service] = lambda: ingestion_service
    app.dependency_overrides[get_index_state_service] = lambda: state_service
    app.dependency_overrides[get_chunking_service] = lambda: chunking_service
    app.dependency_overrides[get_embedding_service] = lambda: embedding_service
    app.dependency_overrides[get_vector_index_service] = lambda: vector_service
    app.dependency_overrides[get_reindex_service] = lambda: reindex_service
    app.dependency_overrides[get_retrieval_service] = lambda: retrieval_service

    yield {
        "raw_dir": raw_dir,
        "indexes_dir": indexes_dir,
        "chroma_dir": chroma_dir,
        "ingestion": ingestion_service,
        "state": state_service,
        "chunking": chunking_service,
        "embedding": embedding_service,
        "vector": vector_service,
        "reindex": reindex_service,
        "retrieval": retrieval_service,
    }

    app.dependency_overrides.clear()


# ============================================================================
# Retrieval Tests
# ============================================================================


def test_retrieval_single_indexed_document(retrieval_env):
    """Verify retrieval returns relevant chunks from a single indexed document."""
    ingestion = retrieval_env["ingestion"]
    reindex = retrieval_env["reindex"]

    doc = ingestion.create_and_store_document(
        content="FastAPI is a modern, high-performance web framework for building APIs with Python.\n\n"
                "Uvicorn is a lightning-fast ASGI server implementation used to run FastAPI applications in production.",
        title="fastapi_guide.txt",
        source_type="txt",
    )
    reindex.execute_reindex([doc.document_id])

    payload = {"question": "What ASGI server runs FastAPI in production?"}
    response = client.post("/api/v1/retrieval/search", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert data["chunk_count"] >= 1
    assert data["active_document_count"] == 1
    assert data["threshold"] == 0.50

    top_chunk = data["chunks"][0]
    assert top_chunk["document_id"] == doc.document_id
    assert top_chunk["title"] == "fastapi_guide.txt"
    assert "Uvicorn" in top_chunk["content"]
    assert top_chunk["similarity_score"] >= 0.50


def test_retrieval_multiple_indexed_documents(retrieval_env):
    """Verify retrieval searches across all active indexed documents."""
    ingestion = retrieval_env["ingestion"]
    reindex = retrieval_env["reindex"]

    doc1 = ingestion.create_and_store_document(
        content="BAAI/bge-small-en-v1.5 is a leading embedding model with 384 dimensions.",
        title="embeddings.txt",
        source_type="txt",
    )
    doc2 = ingestion.create_and_store_document(
        content="ChromaDB stores high-dimensional vectors and provides cosine similarity search.",
        title="vectordb.txt",
        source_type="txt",
    )
    reindex.execute_reindex([doc1.document_id, doc2.document_id])

    # Search for embeddings
    res1 = client.post("/api/v1/retrieval/search", json={"question": "Tell me about the 384 dimension embedding model"})
    assert res1.status_code == 200
    assert res1.json()["status"] == "success"
    assert any(c["title"] == "embeddings.txt" for c in res1.json()["chunks"])

    # Search for ChromaDB
    res2 = client.post("/api/v1/retrieval/search", json={"question": "What database performs cosine similarity search?"})
    assert res2.status_code == 200
    assert res2.json()["status"] == "success"
    assert any(c["title"] == "vectordb.txt" for c in res2.json()["chunks"])


def test_unselected_documents_never_returned(retrieval_env):
    """Verify unselected documents in data/raw/ are NEVER returned during retrieval."""
    ingestion = retrieval_env["ingestion"]
    reindex = retrieval_env["reindex"]

    active_doc = ingestion.create_and_store_document(
        content="This is the approved public user guide for the platform.",
        title="public_guide.txt",
        source_type="txt",
    )
    unselected_doc = ingestion.create_and_store_document(
        content="CONFIDENTIAL SECRET: The master key password is banana_apple_12345.",
        title="confidential.txt",
        source_type="txt",
    )

    # Index ONLY the public document
    reindex.execute_reindex([active_doc.document_id])

    # Search specifically for the secret content
    response = client.post("/api/v1/retrieval/search", json={"question": "What is the master key password banana?"})
    assert response.status_code == 200

    data = response.json()
    # Confidential doc must NEVER appear
    for chunk in data["chunks"]:
        assert chunk["document_id"] != unselected_doc.document_id
        assert "banana_apple_12345" not in chunk["content"]


def test_irrelevant_question_produces_no_candidates(retrieval_env):
    """Verify irrelevant query where all candidates score below threshold returns no_candidates."""
    ingestion = retrieval_env["ingestion"]
    reindex = retrieval_env["reindex"]

    doc = ingestion.create_and_store_document(
        content="Python web development with FastAPI and Pydantic validation.",
        title="python_api.txt",
        source_type="txt",
    )
    reindex.execute_reindex([doc.document_id])

    # Query completely unrelated to Python APIs
    response = client.post(
        "/api/v1/retrieval/search",
        json={"question": "How to bake a chocolate strawberry sourdough cake at 350 degrees?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "no_candidates"
    assert data["chunks"] == []
    assert data["chunk_count"] == 0


def test_retrieval_top_k_override(retrieval_env):
    """Verify top_k override restricts returned chunks."""
    ingestion = retrieval_env["ingestion"]
    reindex = retrieval_env["reindex"]

    paragraphs = "\n\n".join([f"Paragraph number {i} detailing Python software engineering." for i in range(10)])
    doc = ingestion.create_and_store_document(
        content=paragraphs,
        title="long_doc.txt",
        source_type="txt",
    )
    reindex.execute_reindex([doc.document_id])

    response = client.post(
        "/api/v1/retrieval/search",
        json={"question": "software engineering with python", "top_k": 2},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["chunks"]) <= 2


def test_empty_question_rejected():
    """Verify empty or whitespace query is rejected with HTTP 422."""
    response = client.post("/api/v1/retrieval/search", json={"question": "   "})
    assert response.status_code == 422


def test_retrieval_empty_active_index_returns_no_candidates(retrieval_env):
    """Verify retrieval on empty index returns no_candidates without error."""
    response = client.post(
        "/api/v1/retrieval/search",
        json={"question": "Any question when no document is active"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "no_candidates"
    assert data["chunks"] == []
    assert data["active_document_count"] == 0


def test_reindex_swapping_updates_retrieval(retrieval_env):
    """Verify changing the active index set dynamically updates retrieval results."""
    ingestion = retrieval_env["ingestion"]
    reindex = retrieval_env["reindex"]

    doc_a = ingestion.create_and_store_document(
        content="Alpha protocol handles cryptographic key rotation.",
        title="alpha.txt",
        source_type="txt",
    )
    doc_b = ingestion.create_and_store_document(
        content="Beta protocol handles database read replica scaling.",
        title="beta.txt",
        source_type="txt",
    )

    # 1. Index Doc A only
    reindex.execute_reindex([doc_a.document_id])
    res_a = client.post("/api/v1/retrieval/search", json={"question": "How does key rotation work in alpha protocol?"})
    assert res_a.json()["status"] == "success"
    assert res_a.json()["chunks"][0]["title"] == "alpha.txt"

    # 2. Swap active index to Doc B only
    reindex.execute_reindex([doc_b.document_id])

    # Now Alpha query should no longer find Alpha doc
    res_a2 = client.post("/api/v1/retrieval/search", json={"question": "How does key rotation work in alpha protocol?"})
    for chunk in res_a2.json().get("chunks", []):
        assert chunk["title"] != "alpha.txt"

    # Beta query should now succeed
    res_b = client.post("/api/v1/retrieval/search", json={"question": "How does read replica scaling work in beta protocol?"})
    assert res_b.json()["status"] == "success"
    assert res_b.json()["chunks"][0]["title"] == "beta.txt"
