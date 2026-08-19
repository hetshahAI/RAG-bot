import io
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pypdf import PdfReader

from app.core.config import BASE_DIR
from app.models.schemas import (
    DocumentIngestResponse,
    DocumentModel,
    DocumentPage,
    TextIngestRequest,
)
from app.services.interfaces import IIngestionService
from app.services.ocr import OCRService, SUPPORTED_IMAGE_EXTENSIONS, get_ocr_service

logger = logging.getLogger("rag-backend.ingestion")

SUPPORTED_DOCUMENT_EXTENSIONS = {".txt", ".pdf"}.union(SUPPORTED_IMAGE_EXTENSIONS)


class IngestionService(IIngestionService):
    """Service handling normalization, creation, retrieval, and raw storage of documents."""

    def __init__(
        self,
        raw_data_dir: Optional[Path] = None,
        ocr_service: Optional[OCRService] = None,
    ):
        self.raw_data_dir = raw_data_dir or (BASE_DIR / "data" / "raw")
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        self.ocr_service = ocr_service or get_ocr_service()

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize line endings and surrounding whitespace while preserving internal structure."""
        if not text:
            return ""
        # Convert CRLF and CR to standard LF
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        # Strip trailing whitespace on individual lines
        lines = [line.rstrip() for line in normalized.split("\n")]
        # Rejoin lines and strip outer document whitespace
        return "\n".join(lines).strip()

    def create_and_store_document(
        self,
        content: str,
        title: Optional[str],
        source_type: str,
        page_count: Optional[int] = None,
        pages: Optional[List[DocumentPage]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DocumentModel:
        """Normalize content, assemble DocumentModel, and write JSON to raw storage."""
        normalized_content = self.normalize_text(content)
        if not normalized_content:
            raise ValueError("Document content cannot be empty or whitespace only.")

        document_id = f"doc_{uuid.uuid4().hex}"
        created_at = datetime.now(timezone.utc)
        clean_title = title.strip() if title and title.strip() else None

        document = DocumentModel(
            document_id=document_id,
            title=clean_title,
            source_type=source_type,
            content=normalized_content,
            character_count=len(normalized_content),
            page_count=page_count,
            pages=pages,
            metadata=metadata,
            created_at=created_at,
        )

        file_path = self.raw_data_dir / f"{document_id}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(document.model_dump(mode="json"), f, indent=2, ensure_ascii=False)
            logger.info("Successfully stored raw document %s to %s", document_id, file_path)
        except IOError as e:
            logger.error("Failed to write document %s to disk: %s", document_id, e)
            raise RuntimeError(f"Failed to persist raw document to storage: {str(e)}") from e

        return document

    def ingest_text(self, request: TextIngestRequest) -> DocumentModel:
        """Process incoming raw text payload."""
        title = request.title.strip() if request.title and request.title.strip() else None
        return self.create_and_store_document(
            content=request.text,
            title=title,
            source_type="text",
        )

    def _extract_pdf_pages(self, file_bytes: bytes) -> List[DocumentPage]:
        """Extract and normalize text page-by-page from PDF bytes."""
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
        except Exception as e:
            raise ValueError(f"Invalid or corrupted PDF file: {str(e)}") from e

        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as e:
                raise ValueError("Encrypted PDF files are not supported.") from e

        if len(reader.pages) == 0:
            raise ValueError("PDF file contains no pages.")

        pages: List[DocumentPage] = []
        for idx, page in enumerate(reader.pages, start=1):
            try:
                raw_text = page.extract_text() or ""
            except Exception as e:
                logger.warning("Error extracting text from PDF page %d: %s", idx, e)
                raw_text = ""

            normalized_page_text = self.normalize_text(raw_text)
            pages.append(
                DocumentPage(
                    page_number=idx,
                    content=normalized_page_text,
                    character_count=len(normalized_page_text),
                )
            )

        total_chars = sum(p.character_count for p in pages)
        if total_chars == 0:
            raise ValueError("PDF contains no extractable text.")

        return pages

    def ingest_file(self, filename: Optional[str], file_bytes: bytes) -> DocumentModel:
        """Process an uploaded file (.txt, .pdf, or images), validate, extract, and persist."""
        if not filename:
            raise ValueError("Filename is required.")

        ext = Path(filename).suffix.lower()
        if ext not in SUPPORTED_DOCUMENT_EXTENSIONS:
            allowed_list = sorted(list(SUPPORTED_DOCUMENT_EXTENSIONS))
            raise ValueError(
                f"Unsupported file extension '{ext}'. "
                f"Supported file types: {', '.join(allowed_list)}"
            )

        if not file_bytes or len(file_bytes) == 0:
            raise ValueError("Uploaded file is empty.")

        # Handle TXT documents
        if ext == ".txt":
            try:
                content_str = file_bytes.decode("utf-8")
            except UnicodeDecodeError as e:
                raise ValueError("File content must be valid UTF-8 encoded text.") from e

            return self.create_and_store_document(
                content=content_str,
                title=filename,
                source_type="txt",
            )

        # Handle PDF documents
        elif ext == ".pdf":
            pages = self._extract_pdf_pages(file_bytes)
            page_blocks = [f"--- Page {p.page_number} ---\n{p.content}" for p in pages if p.content]
            combined_content = "\n\n".join(page_blocks)

            return self.create_and_store_document(
                content=combined_content,
                title=filename,
                source_type="pdf",
                page_count=len(pages),
                pages=pages,
            )

        # Handle Image documents with OCR
        elif ext in SUPPORTED_IMAGE_EXTENSIONS:
            raw_text, ocr_metadata = self.ocr_service.extract_text_from_image(
                image_bytes=file_bytes,
                filename=filename,
            )
            normalized_text = self.normalize_text(raw_text)
            if not normalized_text:
                raise ValueError("Image contains no readable text.")

            return self.create_and_store_document(
                content=normalized_text,
                title=filename,
                source_type="image",
                metadata=ocr_metadata,
            )

        raise ValueError(f"Unhandled file extension '{ext}'.")

    def list_documents(self) -> List[DocumentModel]:
        """List all uploaded raw documents stored in data/raw/."""
        documents: List[DocumentModel] = []
        for file_path in self.raw_data_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    documents.append(DocumentModel(**data))
            except Exception as e:
                logger.warning("Error reading raw document file %s: %s", file_path, e)

        # Sort documents by created_at descending
        documents.sort(key=lambda d: d.created_at, reverse=True)
        return documents

    def get_document(self, document_id: str) -> Optional[DocumentModel]:
        """Retrieve a specific raw document by its ID."""
        file_path = self.raw_data_dir / f"{document_id}.json"
        if not file_path.exists():
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return DocumentModel(**data)
        except Exception as e:
            logger.error("Failed to parse raw document %s: %s", document_id, e)
            return None

    def get_documents_by_ids(self, document_ids: List[str]) -> Tuple[List[DocumentModel], List[str]]:
        """Retrieve multiple documents by IDs. Returns (found_documents, missing_ids)."""
        found: List[DocumentModel] = []
        missing: List[str] = []

        for doc_id in document_ids:
            doc = self.get_document(doc_id)
            if doc:
                found.append(doc)
            else:
                missing.append(doc_id)

        return found, missing

    @staticmethod
    def to_response(document: DocumentModel) -> DocumentIngestResponse:
        """Convert a DocumentModel to DocumentIngestResponse."""
        return DocumentIngestResponse(
            document_id=document.document_id,
            title=document.title,
            source_type=document.source_type,
            character_count=document.character_count,
            page_count=document.page_count,
            metadata=document.metadata,
            created_at=document.created_at,
        )


def get_ingestion_service() -> IngestionService:
    """Dependency provider for IngestionService."""
    return IngestionService()
