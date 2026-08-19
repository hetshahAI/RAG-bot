import json
from typing import Any, Dict, List, Optional
import pytest
from fastapi.testclient import TestClient

from app.core.config import RetrievalConfig, VectorDBConfig
from app.main import app
from app.models.schemas import RetrievalChunk
from app.services.chroma import ChromaVectorService, get_vector_index_service
from app.services.chunking import ChunkingService, get_chunking_service
from app.services.embeddings import EmbeddingService, get_embedding_service
from app.services.index_state import IndexStateService, get_index_state_service
from app.services.ingestion import IngestionService, get_ingestion_service
from app.services.interfaces import ILLMClient
from app.services.llm import get_llm_client
from app.services.rag import (
    ABSTENTION_ANSWER,
    AnswerValidator,
    ExecutionTracer,
    RAGService,
    get_rag_service,
)
from app.services.reindex import ReindexService, get_reindex_service
from app.services.retrieval import RetrievalService, get_retrieval_service

client = TestClient(app)


class MockLLMClient(ILLMClient):
    """Mock LLM client to simulate various LLM behaviors and inspect prompts."""

    def __init__(
        self,
        response_payload: Optional[Dict[str, Any]] = None,
        raw_response: Optional[str] = None,
        raise_error: bool = False,
    ):
        self.response_payload = response_payload
        self.raw_response = raw_response
        self.raise_error = raise_error
        self.call_count = 0
        self.last_messages: List[Dict[str, str]] = []

    def generate_chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        self.call_count += 1
        self.last_messages = messages

        if self.raise_error:
            raise RuntimeError("Simulated LLM network connection timeout.")

        if self.raw_response is not None:
            return self.raw_response

        if self.response_payload is not None:
            return json.dumps(self.response_payload)

        return json.dumps({
            "status": "answered",
            "answer": "Default mock answer grounded in context.",
            "citations": [],
        })


@pytest.fixture
def rag_env(tmp_path):
    """Fixture providing isolated services and mock LLM for RAG QA testing."""
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
        collection_name="test_rag_qa_collection",
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

    mock_llm = MockLLMClient()
    tracer = ExecutionTracer()
    rag_service = RAGService(
        retrieval_service=retrieval_service,
        llm_client=mock_llm,
        index_state_service=state_service,
        tracer=tracer,
    )

    app.dependency_overrides[get_ingestion_service] = lambda: ingestion_service
    app.dependency_overrides[get_index_state_service] = lambda: state_service
    app.dependency_overrides[get_chunking_service] = lambda: chunking_service
    app.dependency_overrides[get_embedding_service] = lambda: embedding_service
    app.dependency_overrides[get_vector_index_service] = lambda: vector_service
    app.dependency_overrides[get_reindex_service] = lambda: reindex_service
    app.dependency_overrides[get_retrieval_service] = lambda: retrieval_service
    app.dependency_overrides[get_llm_client] = lambda: mock_llm
    app.dependency_overrides[get_rag_service] = lambda: rag_service

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
        "mock_llm": mock_llm,
        "rag_service": rag_service,
        "tracer": tracer,
    }

    app.dependency_overrides.clear()


# ============================================================================
# Unit Tests for AnswerValidator
# ============================================================================


def test_validator_valid_answered_dict_citations():
    """Verify validator accepts valid structured JSON with dict citations."""
    sample_chunk = RetrievalChunk(
        chunk_id="chunk_doc1_0",
        document_id="doc1",
        title="doc1.txt",
        source_type="txt",
        content="FastAPI is modern.",
        similarity_score=0.88,
        metadata={},
    )
    raw = json.dumps({
        "status": "answered",
        "answer": "FastAPI is a modern web framework.",
        "citations": [{"chunk_id": "chunk_doc1_0", "document_id": "doc1", "title": "doc1.txt"}],
    })
    is_valid, reason, data = AnswerValidator.validate(raw, [sample_chunk])
    assert is_valid is True
    assert data["status"] == "answered"
    assert len(data["validated_citations"]) == 1
    assert data["validated_citations"][0].chunk_id == "chunk_doc1_0"


def test_validator_valid_answered_string_citations():
    """Verify validator accepts list of string chunk IDs and resolves them."""
    sample_chunk = RetrievalChunk(
        chunk_id="chunk_doc1_0",
        document_id="doc1",
        title="doc1.txt",
        source_type="txt",
        content="FastAPI is modern.",
        similarity_score=0.88,
        metadata={},
    )
    raw = json.dumps({
        "status": "answered",
        "answer": "FastAPI is a modern web framework.",
        "citations": ["chunk_doc1_0"],
    })
    is_valid, reason, data = AnswerValidator.validate(raw, [sample_chunk])
    assert is_valid is True
    assert data["status"] == "answered"
    assert len(data["validated_citations"]) == 1
    assert data["validated_citations"][0].chunk_id == "chunk_doc1_0"
    assert data["validated_citations"][0].title == "doc1.txt"


def test_validator_invalid_json():
    """Verify validator catches malformed non-JSON output."""
    is_valid, reason, data = AnswerValidator.validate("Not a JSON string", [])
    assert is_valid is False
    assert "not valid JSON" in reason


def test_validator_hallucinated_citation():
    """Verify validator rejects citations referencing unretrieved chunk IDs."""
    sample_chunk = RetrievalChunk(
        chunk_id="chunk_doc1_0",
        document_id="doc1",
        title="doc1.txt",
        source_type="txt",
        content="FastAPI is modern.",
        similarity_score=0.88,
        metadata={},
    )
    raw = json.dumps({
        "status": "answered",
        "answer": "Answer here.",
        "citations": [{"chunk_id": "chunk_fake_999", "document_id": "doc1"}],
    })
    is_valid, reason, data = AnswerValidator.validate(raw, [sample_chunk])
    assert is_valid is False
    assert "unretrieved" in reason


# ============================================================================
# End-to-End RAG QA Pipeline Tests
# ============================================================================


def test_rag_successful_grounded_answer(rag_env):
    """Verify end-to-end grounded answer generation when evidence exists."""
    ingestion = rag_env["ingestion"]
    reindex = rag_env["reindex"]
    mock_llm = rag_env["mock_llm"]

    doc = ingestion.create_and_store_document(
        content="BAAI/bge-small-en-v1.5 is a leading embedding model with 384 dimensions.",
        title="embedding_spec.txt",
        source_type="txt",
    )
    reindex.execute_reindex([doc.document_id])

    # Find chunk ID that was generated
    retrieval_res = rag_env["retrieval"].retrieve("What embedding model is used?")
    assert retrieval_res.status == "success"
    chunk_id = retrieval_res.chunks[0].chunk_id

    # Configure mock LLM response
    mock_llm.response_payload = {
        "status": "answered",
        "answer": "The pipeline uses BAAI/bge-small-en-v1.5 with 384 dimensions.",
        "citations": [
            {
                "chunk_id": chunk_id,
                "document_id": doc.document_id,
                "title": "embedding_spec.txt",
            }
        ],
    }

    response = client.post("/api/v1/rag/ask", json={"question": "What embedding model is used?"})
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "answered"
    assert data["question"] == "What embedding model is used?"

    # Retrieval details
    assert data["retrieval"]["status"] == "success"
    assert data["retrieval"]["chunk_count"] >= 1
    assert len(data["retrieval"]["chunks"]) >= 1

    # LLM details
    assert data["llm"]["status"] == "answered"
    assert "BAAI/bge-small-en-v1.5" in data["llm"]["answer"]
    assert len(data["llm"]["citations"]) == 1
    assert data["llm"]["citations"][0]["chunk_id"] == chunk_id
    assert mock_llm.call_count == 1


def test_rag_multi_chunk_synthesis(rag_env):
    """Verify synthesis across multiple chunks into a unified grounded answer."""
    ingestion = rag_env["ingestion"]
    reindex = rag_env["reindex"]
    mock_llm = rag_env["mock_llm"]

    doc1 = ingestion.create_and_store_document(
        content="Architecture component A handles document ingestion and normalization.",
        title="comp_a.txt",
        source_type="txt",
    )
    doc2 = ingestion.create_and_store_document(
        content="Architecture component B handles dense vector embedding and indexing.",
        title="comp_b.txt",
        source_type="txt",
    )
    reindex.execute_reindex([doc1.document_id, doc2.document_id])

    retrieval_res = rag_env["retrieval"].retrieve("Tell me about components A and B")
    chunk_ids = [c.chunk_id for c in retrieval_res.chunks]

    mock_llm.response_payload = {
        "status": "answered",
        "answer": "Component A handles ingestion and normalization, while Component B handles embedding and indexing.",
        "citations": chunk_ids,
    }

    response = client.post("/api/v1/rag/ask", json={"question": "Tell me about components A and B"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert len(data["llm"]["citations"]) >= 2
    assert "Component A" in data["llm"]["answer"]
    assert "Component B" in data["llm"]["answer"]


def test_rag_irrelevant_question_no_candidates_no_llm_call(rag_env):
    """Verify irrelevant query with 0 candidate chunks passes no candidates and skips LLM."""
    ingestion = rag_env["ingestion"]
    reindex = rag_env["reindex"]
    mock_llm = rag_env["mock_llm"]

    doc = ingestion.create_and_store_document(
        content="Python web development with FastAPI and Pydantic validation.",
        title="python_api.txt",
        source_type="txt",
    )
    reindex.execute_reindex([doc.document_id])

    response = client.post(
        "/api/v1/rag/ask",
        json={"question": "What is the recipe for chocolate strawberry sourdough bread at 350 degrees?"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "insufficient_evidence"
    assert data["llm"]["status"] == "insufficient_evidence"
    assert data["llm"]["answer"] == ABSTENTION_ANSWER
    assert data["llm"]["citations"] == []
    assert data["retrieval"]["chunk_count"] == 0
    assert data["retrieval"]["chunks"] == []
    # Strict Guardrail: LLM MUST NOT BE CALLED when no candidates exist
    assert mock_llm.call_count == 0


def test_rag_empty_active_index_no_llm_call(rag_env):
    """Verify empty active knowledge base immediately abstains without calling LLM."""
    mock_llm = rag_env["mock_llm"]

    response = client.post("/api/v1/rag/ask", json={"question": "Tell me about anything"})
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "insufficient_evidence"
    assert data["llm"]["answer"] == ABSTENTION_ANSWER
    assert data["retrieval"]["chunk_count"] == 0
    assert mock_llm.call_count == 0


def test_rag_selected_documents_only(rag_env):
    """Verify context passed to LLM contains ONLY active selected documents."""
    ingestion = rag_env["ingestion"]
    reindex = rag_env["reindex"]
    mock_llm = rag_env["mock_llm"]

    doc_active = ingestion.create_and_store_document(
        content="ACTIVE PUBLIC GUIDE: System operates on port 8000.",
        title="active_guide.txt",
        source_type="txt",
    )
    doc_unselected = ingestion.create_and_store_document(
        content="CONFIDENTIAL UNSELECTED: Database root password is topsecretpass123.",
        title="secret.txt",
        source_type="txt",
    )
    reindex.execute_reindex([doc_active.document_id])

    client.post("/api/v1/rag/ask", json={"question": "What port does the system operate on?"})

    assert mock_llm.call_count == 1
    prompt_text = "".join([m["content"] for m in mock_llm.last_messages])
    assert "ACTIVE PUBLIC GUIDE" in prompt_text
    assert "topsecretpass123" not in prompt_text
    assert "CONFIDENTIAL UNSELECTED" not in prompt_text


def test_rag_llm_decides_insufficient_evidence_preserves_retrieval_chunks(rag_env):
    """Verify when LLM decides context is insufficient, candidate chunks are preserved in response."""
    ingestion = rag_env["ingestion"]
    reindex = rag_env["reindex"]
    mock_llm = rag_env["mock_llm"]

    doc = ingestion.create_and_store_document(
        content="The server was started at 10:00 AM on Monday.",
        title="server_log.txt",
        source_type="txt",
    )
    reindex.execute_reindex([doc.document_id])

    mock_llm.response_payload = {
        "status": "insufficient_evidence",
        "answer": "The server logs state the start time, but do not mention who stopped the server.",
        "citations": [],
    }

    response = client.post("/api/v1/rag/ask", json={"question": "Who stopped the server at 11:00 AM?"})
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "insufficient_evidence"
    assert data["llm"]["status"] == "insufficient_evidence"
    assert data["llm"]["answer"] == ABSTENTION_ANSWER

    # IMPORTANT: Retrieved candidate chunks MUST be preserved in the response for inspection!
    assert data["retrieval"]["status"] == "success"
    assert data["retrieval"]["chunk_count"] >= 1
    assert len(data["retrieval"]["chunks"]) >= 1
    assert data["retrieval"]["chunks"][0]["title"] == "server_log.txt"


def test_rag_malformed_llm_response_safe_abstention(rag_env):
    """Verify malformed non-JSON output from LLM safely returns abstention."""
    ingestion = rag_env["ingestion"]
    reindex = rag_env["reindex"]
    mock_llm = rag_env["mock_llm"]

    doc = ingestion.create_and_store_document(
        content="Kubernetes manages container deployments.",
        title="k8s.txt",
        source_type="txt",
    )
    reindex.execute_reindex([doc.document_id])

    mock_llm.raw_response = "I am an AI and here is some random text without JSON formatting."

    response = client.post("/api/v1/rag/ask", json={"question": "How does Kubernetes work?"})
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "insufficient_evidence"
    assert data["llm"]["answer"] == ABSTENTION_ANSWER
    assert data["retrieval"]["chunk_count"] >= 1


def test_rag_invalid_citation_safe_abstention(rag_env):
    """Verify hallucinated citation causes validator rejection and safe abstention."""
    ingestion = rag_env["ingestion"]
    reindex = rag_env["reindex"]
    mock_llm = rag_env["mock_llm"]

    doc = ingestion.create_and_store_document(
        content="Docker containers isolate software dependencies.",
        title="docker.txt",
        source_type="txt",
    )
    reindex.execute_reindex([doc.document_id])

    mock_llm.response_payload = {
        "status": "answered",
        "answer": "Docker isolates dependencies.",
        "citations": [{"chunk_id": "non_existent_chunk_12345", "document_id": "fake_doc"}],
    }

    response = client.post("/api/v1/rag/ask", json={"question": "What does Docker do?"})
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "insufficient_evidence"
    assert data["llm"]["answer"] == ABSTENTION_ANSWER


def test_rag_llm_failure_safe_abstention(rag_env):
    """Verify LLM network failure returns safe abstention without 500 crash."""
    ingestion = rag_env["ingestion"]
    reindex = rag_env["reindex"]
    mock_llm = rag_env["mock_llm"]

    doc = ingestion.create_and_store_document(
        content="PostgreSQL supports ACID compliance.",
        title="postgres.txt",
        source_type="txt",
    )
    reindex.execute_reindex([doc.document_id])

    mock_llm.raise_error = True

    response = client.post("/api/v1/rag/ask", json={"question": "What does PostgreSQL support?"})
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "insufficient_evidence"
    assert data["llm"]["answer"] == ABSTENTION_ANSWER


def test_rag_execution_trace_nodes_and_no_secrets(rag_env):
    """Verify execution trace records all lifecycle nodes and leaks no secrets."""
    ingestion = rag_env["ingestion"]
    reindex = rag_env["reindex"]
    mock_llm = rag_env["mock_llm"]

    doc = ingestion.create_and_store_document(
        content="Redis is an in-memory data structure store used as a database, cache, and message broker.",
        title="redis.txt",
        source_type="txt",
    )
    reindex.execute_reindex([doc.document_id])

    retrieval_res = rag_env["retrieval"].retrieve("What is Redis used for?")
    chunk_id = retrieval_res.chunks[0].chunk_id
    mock_llm.response_payload = {
        "status": "answered",
        "answer": "Redis is an in-memory data store used as a database and cache.",
        "citations": [{"chunk_id": chunk_id, "document_id": doc.document_id, "title": "redis.txt"}],
    }

    ask_res = client.post("/api/v1/rag/ask", json={"question": "What is Redis used for?"})
    assert ask_res.status_code == 200
    run_id = ask_res.json()["run_id"]
    assert run_id.startswith("run_")

    # Fetch execution trace
    trace_res = client.get(f"/api/v1/rag/runs/{run_id}")
    assert trace_res.status_code == 200

    trace = trace_res.json()
    assert trace["run_id"] == run_id
    assert trace["question"] == "What is Redis used for?"
    assert trace["active_document_count"] == 1

    events = trace["events"]
    node_names = [e["node"] for e in events]
    required_nodes = ["query", "embedding", "retrieval", "context_builder", "llm", "validator", "answer"]
    for req_node in required_nodes:
        assert req_node in node_names

    # Check timing metrics are present and non-negative
    for e in events:
        assert "duration_ms" in e
        assert e["duration_ms"] >= 0.0

    # Check that secrets or API keys are NOT leaked
    trace_dump_str = json.dumps(trace).lower()
    assert "sk-" not in trace_dump_str
    assert "bearer " not in trace_dump_str


def test_rag_run_id_unique_and_not_found(rag_env):
    """Verify run_id is unique across requests and invalid run_id returns HTTP 404."""
    # 404 check
    res_404 = client.get("/api/v1/rag/runs/run_unrecognized_999999")
    assert res_404.status_code == 404
    assert "not found" in res_404.json()["detail"]

    # Unique check
    res1 = client.post("/api/v1/rag/ask", json={"question": "First question"})
    res2 = client.post("/api/v1/rag/ask", json={"question": "Second question"})
    assert res1.json()["run_id"] != res2.json()["run_id"]
