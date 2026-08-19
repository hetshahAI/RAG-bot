import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import BASE_DIR, VectorDBConfig, settings
from app.models.schemas import Chunk
from app.services.interfaces import IVectorIndexService

logger = logging.getLogger("rag-backend.chroma")

EXPECTED_EMBEDDING_DIMENSION = 384


def sanitize_metadata_for_chroma(raw_meta: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize metadata dictionary to ensure all values are valid ChromaDB primitives (str, int, float, bool)."""
    sanitized: Dict[str, Any] = {}
    for k, v in raw_meta.items():
        if v is None:
            continue
        elif isinstance(v, (str, int, float, bool)):
            sanitized[k] = v
        elif isinstance(v, (list, dict)):
            sanitized[k] = json.dumps(v, ensure_ascii=False)
        else:
            sanitized[k] = str(v)
    return sanitized


def restore_metadata_from_chroma(sanitized_meta: Dict[str, Any]) -> Dict[str, Any]:
    """Restore JSON-encoded complex structures in metadata dictionaries."""
    restored: Dict[str, Any] = {}
    for k, v in sanitized_meta.items():
        if isinstance(v, str) and (v.startswith("{") or v.startswith("[")):
            try:
                restored[k] = json.loads(v)
            except Exception:
                restored[k] = v
        else:
            restored[k] = v
    return restored


class ChromaVectorService(IVectorIndexService):
    """Local persistent ChromaDB vector index service implementing IVectorIndexService."""

    def __init__(
        self,
        config: Optional[VectorDBConfig] = None,
        persist_directory: Optional[Path] = None,
    ):
        self.config = config or settings.rag.vector_db
        if persist_directory is not None:
            self.persist_directory = Path(persist_directory).resolve()
        else:
            rel_path = Path(self.config.persist_directory)
            self.persist_directory = (BASE_DIR / rel_path).resolve() if not rel_path.is_absolute() else rel_path

        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.default_collection_name = self.config.collection_name
        self.batch_size = self.config.batch_size or 100
        self.dimension = EXPECTED_EMBEDDING_DIMENSION

        self._client = None

    def _get_client(self):
        """Lazy initialization of Chroma persistent client."""
        if self._client is None:
            import chromadb

            logger.info("Initializing ChromaDB PersistentClient at '%s'", self.persist_directory)
            self._client = chromadb.PersistentClient(path=str(self.persist_directory))
        return self._client

    def _resolve_collection_name(self, collection_name: Optional[str] = None) -> str:
        return collection_name or self.default_collection_name

    def collection_exists(self, collection_name: Optional[str] = None) -> bool:
        """Check if collection exists in Chroma database."""
        target = self._resolve_collection_name(collection_name)
        client = self._get_client()
        try:
            client.get_collection(target)
            return True
        except Exception:
            return False

    def create_collection_if_not_exists(self, collection_name: Optional[str] = None) -> Any:
        """Ensure collection exists in ChromaDB with cosine distance metric."""
        target = self._resolve_collection_name(collection_name)
        client = self._get_client()
        metric = self.config.distance_metric.lower() if self.config.distance_metric else "cosine"
        return client.get_or_create_collection(
            name=target,
            metadata={"hnsw:space": metric},
        )

    def get_collection_info(self, collection_name: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve collection metadata, point count, and persistence path."""
        target = self._resolve_collection_name(collection_name)
        client = self._get_client()
        exists = self.collection_exists(target)
        count = 0

        if exists:
            try:
                col = client.get_collection(target)
                count = col.count()
            except Exception as e:
                logger.warning("Error fetching count for collection '%s': %s", target, e)
                count = 0

        return {
            "provider": "chromadb",
            "collection_name": target,
            "collection_exists": exists,
            "vector_dimension": self.dimension,
            "point_count": count,
            "persistence_path": str(self.persist_directory),
        }

    def validate_inputs(self, chunks: List[Chunk], embeddings: List[List[float]]) -> None:
        """Strict validation of chunks and vector embeddings before database insertion."""
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Mismatch: Received {len(chunks)} chunk(s) but {len(embeddings)} embedding(s)."
            )

        seen_ids = set()
        for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            # Check content
            if not chunk.content or not chunk.content.strip():
                raise ValueError(f"Chunk at index {idx} (ID: '{chunk.chunk_id}') has empty content.")

            # Check unique IDs
            if chunk.chunk_id in seen_ids:
                raise ValueError(f"Duplicate chunk ID detected in batch: '{chunk.chunk_id}'.")
            seen_ids.add(chunk.chunk_id)

            # Check embedding dimension
            if len(emb) != self.dimension:
                raise ValueError(
                    f"Embedding at index {idx} has invalid dimension {len(emb)} (expected {self.dimension})."
                )

    def replace_index(
        self,
        collection_name: str,
        chunks: List[Chunk],
        embeddings: List[List[float]],
    ) -> int:
        """Atomically replace active collection with newly chunked and embedded items."""
        target = self._resolve_collection_name(collection_name)

        # 1. Validate inputs before touching database
        self.validate_inputs(chunks, embeddings)

        client = self._get_client()
        metric = self.config.distance_metric.lower() if self.config.distance_metric else "cosine"

        # 2. Reset collection to ensure replacement semantics (never append)
        try:
            if self.collection_exists(target):
                logger.info("Dropping existing collection '%s' for index replacement", target)
                client.delete_collection(target)
            collection = client.create_collection(name=target, metadata={"hnsw:space": metric})
        except Exception as e:
            logger.error("Failed to reset collection '%s': %s", target, e)
            raise RuntimeError(f"Failed to reset ChromaDB collection '{target}': {str(e)}") from e

        if not chunks:
            logger.info("Replacement index created with 0 points")
            return 0

        # 3. Prepare payload lists
        ids: List[str] = []
        docs: List[str] = []
        vectors: List[List[float]] = []
        metadatas: List[Dict[str, Any]] = []

        for chunk, emb in zip(chunks, embeddings):
            ids.append(chunk.chunk_id)
            docs.append(chunk.content)
            vectors.append(emb)

            meta: Dict[str, Any] = {
                "document_id": chunk.document_id,
                "title": chunk.title or "",
                "source_type": chunk.source_type,
                "chunk_index": chunk.chunk_index,
                "character_count": chunk.character_count,
            }
            if chunk.metadata:
                meta.update(chunk.metadata)
            metadatas.append(sanitize_metadata_for_chroma(meta))

        # 4. Batch insertion
        total = len(ids)
        try:
            for start in range(0, total, self.batch_size):
                end = min(start + self.batch_size, total)
                collection.add(
                    ids=ids[start:end],
                    embeddings=vectors[start:end],
                    documents=docs[start:end],
                    metadatas=metadatas[start:end],
                )
            logger.info("Successfully inserted %d points into Chroma collection '%s'", total, target)
            return total
        except Exception as e:
            logger.error("Error inserting points into ChromaDB: %s", e)
            raise RuntimeError(f"ChromaDB batch insertion failed: {str(e)}") from e

    def clear_index(self, collection_name: Optional[str] = None) -> None:
        """Clear all items in the vector collection without affecting raw document storage."""
        target = self._resolve_collection_name(collection_name)
        client = self._get_client()
        try:
            if self.collection_exists(target):
                logger.info("Deleting collection '%s' to clear vector store", target)
                client.delete_collection(target)
            metric = self.config.distance_metric.lower() if self.config.distance_metric else "cosine"
            client.create_collection(name=target, metadata={"hnsw:space": metric})
            logger.info("Cleared and recreated empty collection '%s'", target)
        except Exception as e:
            logger.error("Failed to clear Chroma collection '%s': %s", target, e)
            raise RuntimeError(f"Failed to clear ChromaDB collection '{target}': {str(e)}") from e

    def query_similarity(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        collection_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query nearest vector neighbors and return matches with cosine similarity scores (1 - cosine_distance)."""
        if len(query_embedding) != self.dimension:
            raise ValueError(
                f"Query embedding has invalid dimension {len(query_embedding)} (expected {self.dimension})."
            )

        target = self._resolve_collection_name(collection_name)
        if not self.collection_exists(target):
            return []

        client = self._get_client()
        collection = client.get_collection(target)
        count = collection.count()
        if count == 0:
            return []

        n_results = min(max(1, top_k), count)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        hits: List[Dict[str, Any]] = []
        for chunk_id, doc_text, meta_dict, dist in zip(ids, docs, metas, distances):
            # In Chroma cosine distance d = 1 - cos(theta), where cos(theta) is cosine similarity
            # Therefore similarity score s = 1.0 - d
            dist_val = float(dist) if dist is not None else 1.0
            similarity = max(0.0, min(1.0, 1.0 - dist_val))

            restored_meta = restore_metadata_from_chroma(meta_dict or {})
            doc_id = restored_meta.pop("document_id", "")
            title = restored_meta.pop("title", None)
            source_type = restored_meta.pop("source_type", "text")
            # Remove redundant top-level fields from nested metadata dictionary
            restored_meta.pop("chunk_index", None)
            restored_meta.pop("character_count", None)

            hits.append(
                {
                    "chunk_id": chunk_id,
                    "document_id": doc_id,
                    "title": title,
                    "source_type": source_type,
                    "content": doc_text,
                    "similarity_score": round(similarity, 4),
                    "metadata": restored_meta,
                }
            )

        # Sort by highest similarity score first
        hits.sort(key=lambda x: x["similarity_score"], reverse=True)
        return hits


_chroma_service_instance: Optional[ChromaVectorService] = None


def get_vector_index_service() -> IVectorIndexService:
    """Dependency provider for vector database service."""
    global _chroma_service_instance
    if _chroma_service_instance is None:
        _chroma_service_instance = ChromaVectorService()
    return _chroma_service_instance
