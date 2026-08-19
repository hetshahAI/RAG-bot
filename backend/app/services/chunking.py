import logging
from typing import Any, Dict, List, Optional

from app.core.config import ChunkingConfig, settings
from app.models.schemas import Chunk, ChunkStatistics, DocumentModel
from app.services.interfaces import IChunkingService

logger = logging.getLogger("rag-backend.chunking")


class ChunkingService(IChunkingService):
    """Deterministic chunking service that respects document boundaries and metadata."""

    def __init__(self, config: Optional[ChunkingConfig] = None):
        self.config = config or settings.rag.chunking

    def split_text(self, text: str, chunk_size: Optional[int] = None, chunk_overlap: Optional[int] = None) -> List[str]:
        """Deterministically split text into overlapping chunks with natural boundary preference."""
        if not text or not text.strip():
            return []

        c_size = chunk_size or self.config.chunk_size
        c_overlap = chunk_overlap or self.config.chunk_overlap

        # Ensure valid overlap
        if c_overlap >= c_size:
            c_overlap = max(0, c_size - 1)

        text = text.strip()
        if len(text) <= c_size:
            return [text]

        chunks: List[str] = []
        start = 0

        while start < len(text):
            end = min(start + c_size, len(text))

            # Look for natural breakpoint if not at end
            if end < len(text):
                search_start = max(start + (c_size // 2), end - c_overlap)
                sub = text[search_start:end]

                best_split = -1
                for delim in ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " "]:
                    pos = sub.rfind(delim)
                    if pos != -1:
                        best_split = search_start + pos + len(delim)
                        break

                if best_split != -1 and best_split > start:
                    end = best_split

            chunk_content = text[start:end].strip()
            if chunk_content:
                chunks.append(chunk_content)

            if end >= len(text):
                break

            start = max(start + 1, end - c_overlap)

        return chunks

    def chunk_document(self, document: DocumentModel) -> List[Chunk]:
        """Generate deterministic chunks for a single DocumentModel preserving metadata."""
        chunks: List[Chunk] = []
        chunk_index = 0

        # Handle Paginated Documents (e.g. PDF)
        if document.source_type == "pdf" and document.pages:
            for page in document.pages:
                if not page.content or not page.content.strip():
                    continue

                page_text_chunks = self.split_text(page.content)
                for text_chunk in page_text_chunks:
                    chunk_id = f"{document.document_id}_c{chunk_index:04d}"
                    metadata: Dict[str, Any] = {
                        "page_number": page.page_number,
                        "source_type": "pdf",
                        "title": document.title,
                    }
                    if document.metadata:
                        metadata.update(document.metadata)

                    chunks.append(
                        Chunk(
                            chunk_id=chunk_id,
                            document_id=document.document_id,
                            source_type=document.source_type,
                            title=document.title,
                            content=text_chunk,
                            chunk_index=chunk_index,
                            character_count=len(text_chunk),
                            metadata=metadata,
                        )
                    )
                    chunk_index += 1

        else:
            # Handle text, txt, images
            text_chunks = self.split_text(document.content)
            for text_chunk in text_chunks:
                chunk_id = f"{document.document_id}_c{chunk_index:04d}"
                metadata = {
                    "source_type": document.source_type,
                    "title": document.title,
                }
                if document.metadata:
                    metadata.update(document.metadata)

                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        document_id=document.document_id,
                        source_type=document.source_type,
                        title=document.title,
                        content=text_chunk,
                        chunk_index=chunk_index,
                        character_count=len(text_chunk),
                        metadata=metadata,
                    )
                )
                chunk_index += 1

        return chunks

    def chunk_documents(self, documents: List[DocumentModel]) -> List[Chunk]:
        """Chunk a list of documents in order."""
        all_chunks: List[Chunk] = []
        for doc in documents:
            all_chunks.extend(self.chunk_document(doc))
        return all_chunks

    def compute_statistics(self, chunks: List[Chunk]) -> ChunkStatistics:
        """Compute statistical breakdown of generated chunks."""
        total = len(chunks)
        if total == 0:
            return ChunkStatistics(
                avg_chunk_size=0.0,
                min_chunk_size=0,
                max_chunk_size=0,
                total_chunks=0,
                chunks_by_source_type={},
            )

        sizes = [c.character_count for c in chunks]
        by_source: Dict[str, int] = {}
        for c in chunks:
            by_source[c.source_type] = by_source.get(c.source_type, 0) + 1

        return ChunkStatistics(
            avg_chunk_size=round(sum(sizes) / total, 2),
            min_chunk_size=min(sizes),
            max_chunk_size=max(sizes),
            total_chunks=total,
            chunks_by_source_type=by_source,
        )


def get_chunking_service() -> ChunkingService:
    """Dependency provider for ChunkingService."""
    return ChunkingService()
