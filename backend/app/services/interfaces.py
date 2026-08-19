from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from app.models.schemas import (
    Chunk,
    ChunkStatistics,
    DocumentModel,
    IndexStateModel,
    RAGAskResponse,
    RAGExecutionTrace,
    RetrievalResponse,
)


class IIngestionService(ABC):
    """Interface for document ingestion and raw storage operations."""

    @abstractmethod
    def list_documents(self) -> List[DocumentModel]:
        """List all raw documents."""
        pass

    @abstractmethod
    def get_document(self, document_id: str) -> Optional[DocumentModel]:
        """Retrieve a specific raw document by ID."""
        pass

    @abstractmethod
    def get_documents_by_ids(self, document_ids: List[str]) -> Tuple[List[DocumentModel], List[str]]:
        """Retrieve multiple documents by ID list."""
        pass


class IChunkingService(ABC):
    """Interface for document chunking and text splitting."""

    @abstractmethod
    def chunk_document(self, document: DocumentModel) -> List[Chunk]:
        """Chunk a single document."""
        pass

    @abstractmethod
    def chunk_documents(self, documents: List[DocumentModel]) -> List[Chunk]:
        """Chunk a list of documents."""
        pass

    @abstractmethod
    def compute_statistics(self, chunks: List[Chunk]) -> ChunkStatistics:
        """Compute statistical breakdown for chunks."""
        pass


class IEmbeddingService(ABC):
    """Interface for dense vector embedding generation."""

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generate dense vector embedding for a single text."""
        pass

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate dense vector embeddings for multiple texts."""
        pass

    @abstractmethod
    def embed_chunks(self, chunks: List[Chunk]) -> List[List[float]]:
        """Generate dense vector embeddings for a list of chunks."""
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """Return embedding vector dimension."""
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Return model metadata and configuration."""
        pass


class IVectorIndexService(ABC):
    """Interface for vector database index management and storage."""

    @abstractmethod
    def create_collection_if_not_exists(self, collection_name: Optional[str] = None) -> Any:
        """Ensure collection exists in vector database."""
        pass

    @abstractmethod
    def replace_index(
        self,
        collection_name: Optional[str] = None,
        chunks: Optional[List[Chunk]] = None,
        embeddings: Optional[List[List[float]]] = None,
    ) -> int:
        """Atomically replace active vector index collection with newly chunked and embedded items."""
        pass

    @abstractmethod
    def clear_index(self, collection_name: Optional[str] = None) -> None:
        """Clear/truncate the vector index collection."""
        pass

    @abstractmethod
    def collection_exists(self, collection_name: Optional[str] = None) -> bool:
        """Check if vector collection exists."""
        pass

    @abstractmethod
    def get_collection_info(self, collection_name: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve metadata and item count for vector collection."""
        pass

    @abstractmethod
    def query_similarity(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        collection_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query nearest vector neighbors, converting distance to cosine similarity score."""
        pass


class IIndexStateService(ABC):
    """Interface for managing persistent indexing state."""

    @abstractmethod
    def get_state(self) -> IndexStateModel:
        """Get current index state."""
        pass

    @abstractmethod
    def set_active_documents(self, document_ids: List[str]) -> IndexStateModel:
        """Set the active indexed document set."""
        pass

    @abstractmethod
    def clear_active_documents(self) -> IndexStateModel:
        """Clear active indexed document set."""
        pass

    @abstractmethod
    def is_active(self, document_id: str) -> bool:
        """Check if a document ID is active."""
        pass


class IRetrievalService(ABC):
    """Interface for grounded knowledge-base retrieval."""

    @abstractmethod
    def retrieve(
        self,
        question: str,
        top_k: Optional[int] = None,
    ) -> RetrievalResponse:
        """Retrieve relevant grounded chunks from the active vector index."""
        pass


class ILLMClient(ABC):
    """Interface for LLM completion requests."""

    @abstractmethod
    def generate_chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """Execute chat completion request against configured LLM provider and return raw response string."""
        pass


class IRAGService(ABC):
    """Interface for full strict grounded RAG QA pipeline."""

    @abstractmethod
    def ask(
        self,
        question: str,
        top_k: Optional[int] = None,
    ) -> RAGAskResponse:
        """Answer user question using strict grounded knowledge-base context."""
        pass

    @abstractmethod
    def get_run_trace(self, run_id: str) -> Optional[RAGExecutionTrace]:
        """Retrieve execution trace for a given run ID."""
        pass
