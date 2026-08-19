import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_YAML_PATH = BASE_DIR / "config.yaml"
ENV_PATH = BASE_DIR / ".env"


class AppConfig(BaseModel):
    name: str = "RAG Pipeline Backend"
    version: str = "0.1.0"
    description: str = "FastAPI Backend for Modular RAG Pipeline"
    api_prefix: str = "/api/v1"


class OCRConfig(BaseModel):
    enabled: bool = True
    engine: str = "tesseract"
    language: str = "eng"
    tesseract_cmd: Optional[str] = None


class EmbeddingConfig(BaseModel):
    model_name: str = "BAAI/bge-small-en-v1.5"
    dimension: int = 384
    batch_size: int = 32
    device: str = "cpu"
    normalize_embeddings: bool = True


class ChunkingConfig(BaseModel):
    chunk_size: int = 512
    chunk_overlap: int = 64
    separator: str = "\n\n"


class VectorDBConfig(BaseModel):
    provider: str = "chromadb"
    collection_name: str = "rag_documents"
    persist_directory: str = "data/indexes/chroma"
    distance_metric: str = "cosine"
    batch_size: int = 100


class RetrievalConfig(BaseModel):
    top_k: int = 5
    candidate_k: int = 10
    similarity_threshold: float = 0.50
    min_relevant_chunks: int = 1
    max_context_chunks: int = 10


class LLMConfig(BaseModel):
    provider: str = "openai-compatible"
    base_url: str = "https://exo.manysphere.info/v1"
    model: str = "mlx-community/Qwen3.6-35B-A3B-4bit"
    temperature: float = 0.0
    max_tokens: int = 1024
    timeout_seconds: int = 60


class RAGConfig(BaseModel):
    ocr: OCRConfig = Field(default_factory=OCRConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    vector_db: VectorDBConfig = Field(default_factory=VectorDBConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)


def load_yaml_config(file_path: Path = CONFIG_YAML_PATH) -> Dict[str, Any]:
    """Load and parse the YAML configuration file."""
    if not file_path.exists():
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        content = yaml.safe_load(f)
        return content if isinstance(content, dict) else {}


class Settings(BaseSettings):
    """Application settings combining .env secrets and config.yaml non-secrets."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH) if ENV_PATH.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment & Server
    app_env: str = Field(default="development", alias="APP_ENV")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    debug: bool = Field(default=True, alias="DEBUG")
    cors_origins: Union[List[str], str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        alias="CORS_ORIGINS",
    )

    # OCR binary override (optional)
    tesseract_cmd: Optional[str] = Field(default=None, alias="TESSERACT_CMD")

    # LLM Provider Secrets & Overrides
    llm_provider: Optional[str] = Field(default=None, alias="LLM_PROVIDER")
    llm_api_key: Optional[str] = Field(default=None, alias="LLM_API_KEY")
    llm_base_url: Optional[str] = Field(default=None, alias="LLM_BASE_URL")
    llm_model: Optional[str] = Field(default=None, alias="LLM_MODEL")

    # Structured YAML Configurations
    app: AppConfig = Field(default_factory=AppConfig)
    rag: RAGConfig = Field(default_factory=RAGConfig)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json

                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    @classmethod
    def create(cls) -> "Settings":
        """Factory to load YAML configuration and layer environment variables on top."""
        yaml_data = load_yaml_config()
        instance = cls(**yaml_data)

        # Layer env overrides onto rag.llm if provided
        if instance.llm_provider:
            instance.rag.llm.provider = instance.llm_provider
        if instance.llm_base_url:
            instance.rag.llm.base_url = instance.llm_base_url
        if instance.llm_model:
            instance.rag.llm.model = instance.llm_model

        return instance


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings.create()


settings = get_settings()
