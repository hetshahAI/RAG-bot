from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_health():
    """Verify GET /health returns exact status and service payload."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "rag-backend",
    }


def test_api_v1_health():
    """Verify GET /api/v1/health returns status and service payload."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "rag-backend",
    }


def test_root_endpoint():
    """Verify GET / metadata endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["service"] == "RAG Pipeline Backend"
