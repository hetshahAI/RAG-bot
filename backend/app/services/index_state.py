import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from app.core.config import BASE_DIR, settings
from app.models.schemas import IndexStateModel
from app.services.interfaces import IIndexStateService

logger = logging.getLogger("rag-backend.index_state")


class IndexStateService(IIndexStateService):
    """Service managing the active indexed document set and index metadata."""

    def __init__(self, state_file_path: Optional[Path] = None):
        self.state_file_path = state_file_path or (BASE_DIR / "data" / "indexes" / "index_state.json")
        self.state_file_path.parent.mkdir(parents=True, exist_ok=True)

    def get_state(self) -> IndexStateModel:
        """Load persistent index state or return default."""
        if not self.state_file_path.exists():
            return IndexStateModel(
                active_document_ids=[],
                indexing_version="v1",
                chunking_config=settings.rag.chunking.model_dump(),
                updated_at=datetime.now(timezone.utc),
            )
        try:
            with open(self.state_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return IndexStateModel(**data)
        except Exception as e:
            logger.warning("Error reading index state file, resetting to default: %s", e)
            return IndexStateModel(
                active_document_ids=[],
                indexing_version="v1",
                chunking_config=settings.rag.chunking.model_dump(),
                updated_at=datetime.now(timezone.utc),
            )

    def save_state(self, state: IndexStateModel) -> None:
        """Save index state to disk."""
        try:
            with open(self.state_file_path, "w", encoding="utf-8") as f:
                json.dump(state.model_dump(mode="json"), f, indent=2)
            logger.info("Saved active index state with %d active document(s)", len(state.active_document_ids))
        except IOError as e:
            logger.error("Failed to write index state to disk: %s", e)
            raise RuntimeError(f"Failed to persist index state: {str(e)}") from e

    def set_active_documents(self, document_ids: List[str]) -> IndexStateModel:
        """Update active document set and persist."""
        seen = set()
        deduped = [d for d in document_ids if not (d in seen or seen.add(d))]

        state = IndexStateModel(
            active_document_ids=deduped,
            indexing_version="v1",
            chunking_config=settings.rag.chunking.model_dump(),
            updated_at=datetime.now(timezone.utc),
        )
        self.save_state(state)
        return state

    def clear_active_documents(self) -> IndexStateModel:
        """Clear active document set without deleting raw files."""
        state = IndexStateModel(
            active_document_ids=[],
            indexing_version="v1",
            chunking_config=settings.rag.chunking.model_dump(),
            updated_at=datetime.now(timezone.utc),
        )
        self.save_state(state)
        return state

    def is_active(self, document_id: str) -> bool:
        """Check if a specific document is in the active index."""
        return document_id in self.get_state().active_document_ids


def get_index_state_service() -> IndexStateService:
    """Dependency provider for IndexStateService."""
    return IndexStateService()
