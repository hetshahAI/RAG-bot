from app.core.config import Settings, get_settings


def test_settings_loading():
    """Verify settings loads YAML configuration correctly."""
    settings = get_settings()
    assert settings.rag.ocr.enabled is True
    assert settings.rag.ocr.engine == "tesseract"
    assert settings.rag.ocr.language == "eng"
    assert settings.rag.embedding.model_name == "BAAI/bge-small-en-v1.5"
    assert settings.rag.embedding.dimension == 384
    assert settings.rag.vector_db.provider == "chromadb"
    assert settings.rag.vector_db.collection_name == "rag_documents"
    assert settings.rag.vector_db.persist_directory == "data/indexes/chroma"
    assert settings.app.api_prefix == "/api/v1"
