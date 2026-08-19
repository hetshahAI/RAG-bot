import io
import json
from pathlib import Path
from typing import List, Optional

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas

from app.main import app
from app.services.ingestion import IngestionService, get_ingestion_service

client = TestClient(app)


@pytest.fixture
def temp_raw_dir(tmp_path):
    """Fixture providing an isolated raw storage directory for tests."""
    temp_dir = tmp_path / "raw"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def generate_pdf_bytes(pages_text: List[str]) -> bytes:
    """Generate in-memory PDF bytes with text on each page."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    for idx, text in enumerate(pages_text):
        if idx > 0:
            c.showPage()
        c.setFont("Helvetica", 12)
        c.drawString(72, 720, text)
    c.save()
    buf.seek(0)
    return buf.getvalue()


def generate_blank_pdf_bytes() -> bytes:
    """Generate in-memory blank PDF with no text."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


def generate_image_bytes(
    text: Optional[str] = None,
    format: str = "PNG",
    size=(600, 150),
) -> bytes:
    """Generate in-memory image bytes with optional clear text for OCR testing."""
    img = Image.new("RGB", size, color=(255, 255, 255))
    if text:
        d = ImageDraw.Draw(img)
        d.text((40, 50), text, fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format=format)
    buf.seek(0)
    return buf.getvalue()


# ============================================================================
# Text Ingestion Tests (/api/v1/ingest/text)
# ============================================================================


def test_text_normalization():
    """Verify normalization handles CRLF, trailing spaces, and outer padding."""
    service = IngestionService()
    raw = "  \r\nHello World!  \r\n\r\n  Paragraph 2  \r\n  "
    normalized = service.normalize_text(raw)
    assert normalized == "Hello World!\n\n  Paragraph 2"


def test_ingest_valid_text_api(temp_raw_dir):
    """Verify successful ingestion via POST /api/v1/ingest/text."""
    test_service = IngestionService(raw_data_dir=temp_raw_dir)
    app.dependency_overrides[get_ingestion_service] = lambda: test_service

    try:
        payload = {
            "text": "  First line.\r\nSecond line.  ",
            "title": "Sample Guide",
        }
        response = client.post("/api/v1/ingest/text", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["title"] == "Sample Guide"
        assert data["source_type"] == "text"
        assert data["character_count"] == len("First line.\nSecond line.")
        assert data["page_count"] is None
        assert "document_id" in data
        assert data["document_id"].startswith("doc_")
        assert "created_at" in data

        # Verify physical file creation and content
        saved_file = temp_raw_dir / f"{data['document_id']}.json"
        assert saved_file.exists()

        with open(saved_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
            assert saved_data["document_id"] == data["document_id"]
            assert saved_data["title"] == "Sample Guide"
            assert saved_data["source_type"] == "text"
            assert saved_data["content"] == "First line.\nSecond line."
            assert saved_data["character_count"] == data["character_count"]
            assert saved_data["page_count"] is None
            assert saved_data["pages"] is None
    finally:
        app.dependency_overrides.clear()


def test_ingest_empty_text_api():
    """Verify empty text is rejected with 422 Unprocessable Entity."""
    payload = {"text": "", "title": "Empty"}
    response = client.post("/api/v1/ingest/text", json=payload)
    assert response.status_code == 422


def test_ingest_whitespace_only_text_api():
    """Verify whitespace-only text is rejected with 422 Unprocessable Entity."""
    payload = {"text": "   \n\t   \r\n   ", "title": "Whitespace"}
    response = client.post("/api/v1/ingest/text", json=payload)
    assert response.status_code == 422


def test_ingest_without_title(temp_raw_dir):
    """Verify text ingestion succeeds when title is omitted."""
    test_service = IngestionService(raw_data_dir=temp_raw_dir)
    app.dependency_overrides[get_ingestion_service] = lambda: test_service

    try:
        payload = {"text": "Simple content without title."}
        response = client.post("/api/v1/ingest/text", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] is None
        assert data["character_count"] == len("Simple content without title.")
    finally:
        app.dependency_overrides.clear()


# ============================================================================
# TXT File Ingestion Tests (/api/v1/ingest/file)
# ============================================================================


def test_ingest_valid_txt_file(temp_raw_dir):
    """Verify successful TXT file upload via POST /api/v1/ingest/file."""
    test_service = IngestionService(raw_data_dir=temp_raw_dir)
    app.dependency_overrides[get_ingestion_service] = lambda: test_service

    try:
        file_content = b"Welcome to RAG Pipeline.\r\nThis is a sample document file.\r\n"
        files = {"file": ("manual.txt", io.BytesIO(file_content), "text/plain")}

        response = client.post("/api/v1/ingest/file", files=files)
        assert response.status_code == 201

        data = response.json()
        assert data["title"] == "manual.txt"
        assert data["source_type"] == "txt"
        assert data["character_count"] == len("Welcome to RAG Pipeline.\nThis is a sample document file.")
        assert data["page_count"] is None
        assert "document_id" in data
        assert data["document_id"].startswith("doc_")
        assert "created_at" in data

        # Check stored raw file
        saved_file = temp_raw_dir / f"{data['document_id']}.json"
        assert saved_file.exists()

        with open(saved_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
            assert saved_data["document_id"] == data["document_id"]
            assert saved_data["title"] == "manual.txt"
            assert saved_data["source_type"] == "txt"
            assert saved_data["content"] == "Welcome to RAG Pipeline.\nThis is a sample document file."
    finally:
        app.dependency_overrides.clear()


def test_ingest_utf8_txt_file(temp_raw_dir):
    """Verify UTF-8 unicode text with accents and emojis is properly ingested."""
    test_service = IngestionService(raw_data_dir=temp_raw_dir)
    app.dependency_overrides[get_ingestion_service] = lambda: test_service

    try:
        unicode_text = "Café — Système d'Information 🚀\n你好世界"
        files = {"file": ("unicode_notes.TXT", io.BytesIO(unicode_text.encode("utf-8")), "text/plain")}

        response = client.post("/api/v1/ingest/file", files=files)
        assert response.status_code == 201

        data = response.json()
        assert data["title"] == "unicode_notes.TXT"
        assert data["source_type"] == "txt"

        saved_file = temp_raw_dir / f"{data['document_id']}.json"
        with open(saved_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
            assert saved_data["content"] == unicode_text
    finally:
        app.dependency_overrides.clear()


def test_ingest_empty_txt_file():
    """Verify 0-byte TXT file is rejected with HTTP 400."""
    files = {"file": ("empty.txt", io.BytesIO(b""), "text/plain")}
    response = client.post("/api/v1/ingest/file", files=files)
    assert response.status_code == 400
    assert "Uploaded file is empty" in response.json()["detail"]


def test_ingest_whitespace_only_txt_file():
    """Verify whitespace-only TXT file is rejected with HTTP 400."""
    files = {"file": ("spaces.txt", io.BytesIO(b"   \r\n\t   \n  "), "text/plain")}
    response = client.post("/api/v1/ingest/file", files=files)
    assert response.status_code == 400
    assert "Document content cannot be empty" in response.json()["detail"]


def test_ingest_unsupported_file_extension():
    """Verify unsupported files (e.g. .docx, .zip) are rejected with HTTP 400."""
    unsupported_files = [
        ("document.docx", b"PK\x03\x04...", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("archive.zip", b"PK...", "application/zip"),
    ]

    for filename, content, mime in unsupported_files:
        files = {"file": (filename, io.BytesIO(content), mime)}
        response = client.post("/api/v1/ingest/file", files=files)
        assert response.status_code == 400
        assert "Unsupported file extension" in response.json()["detail"]


# ============================================================================
# PDF File Ingestion Tests (/api/v1/ingest/file)
# ============================================================================


def test_ingest_single_page_pdf(temp_raw_dir):
    """Verify single-page PDF upload and extraction."""
    test_service = IngestionService(raw_data_dir=temp_raw_dir)
    app.dependency_overrides[get_ingestion_service] = lambda: test_service

    try:
        pdf_bytes = generate_pdf_bytes(["Introduction to RAG Pipelines"])
        files = {"file": ("overview.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

        response = client.post("/api/v1/ingest/file", files=files)
        assert response.status_code == 201

        data = response.json()
        assert data["title"] == "overview.pdf"
        assert data["source_type"] == "pdf"
        assert data["page_count"] == 1
        assert data["character_count"] > 0
        assert "document_id" in data

        # Check raw JSON storage
        saved_file = temp_raw_dir / f"{data['document_id']}.json"
        assert saved_file.exists()

        with open(saved_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
            assert saved_data["document_id"] == data["document_id"]
            assert saved_data["source_type"] == "pdf"
            assert saved_data["page_count"] == 1
            assert len(saved_data["pages"]) == 1
            assert saved_data["pages"][0]["page_number"] == 1
            assert "Introduction to RAG Pipelines" in saved_data["pages"][0]["content"]
            assert "--- Page 1 ---" in saved_data["content"]
    finally:
        app.dependency_overrides.clear()


def test_ingest_multi_page_pdf(temp_raw_dir):
    """Verify multi-page PDF preserves page boundaries and numbers."""
    test_service = IngestionService(raw_data_dir=temp_raw_dir)
    app.dependency_overrides[get_ingestion_service] = lambda: test_service

    try:
        pages = [
            "Chapter 1: Architecture overview and components",
            "Chapter 2: Vector embedding and similarity indexing",
            "Chapter 3: Generation and retrieval evaluation",
        ]
        pdf_bytes = generate_pdf_bytes(pages)
        files = {"file": ("manual_v2.PDF", io.BytesIO(pdf_bytes), "application/pdf")}

        response = client.post("/api/v1/ingest/file", files=files)
        assert response.status_code == 201

        data = response.json()
        assert data["title"] == "manual_v2.PDF"
        assert data["source_type"] == "pdf"
        assert data["page_count"] == 3

        # Check raw JSON storage
        saved_file = temp_raw_dir / f"{data['document_id']}.json"
        assert saved_file.exists()

        with open(saved_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
            assert saved_data["page_count"] == 3
            assert len(saved_data["pages"]) == 3
            for i in range(3):
                assert saved_data["pages"][i]["page_number"] == i + 1
                assert pages[i] in saved_data["pages"][i]["content"]
                assert f"--- Page {i + 1} ---" in saved_data["content"]
    finally:
        app.dependency_overrides.clear()


def test_ingest_blank_pdf():
    """Verify PDF with no extractable text is rejected with HTTP 400."""
    pdf_bytes = generate_blank_pdf_bytes()
    files = {"file": ("blank.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    response = client.post("/api/v1/ingest/file", files=files)
    assert response.status_code == 400
    assert "PDF contains no extractable text" in response.json()["detail"]


def test_ingest_corrupted_pdf():
    """Verify corrupted / invalid PDF bytes are rejected with HTTP 400."""
    corrupted_bytes = b"%PDF-1.4\n%invalid-corrupted-binary-content-here\x00\xff"
    files = {"file": ("corrupted.pdf", io.BytesIO(corrupted_bytes), "application/pdf")}

    response = client.post("/api/v1/ingest/file", files=files)
    assert response.status_code == 400
    assert "Invalid or corrupted PDF file" in response.json()["detail"]


# ============================================================================
# Image OCR Ingestion Tests (/api/v1/ingest/file)
# ============================================================================


def test_ingest_png_with_text(temp_raw_dir):
    """Verify PNG image text extraction and metadata preservation via OCR."""
    test_service = IngestionService(raw_data_dir=temp_raw_dir)
    app.dependency_overrides[get_ingestion_service] = lambda: test_service

    try:
        png_bytes = generate_image_bytes(text="INVOICE NUMBER 1024", format="PNG")
        files = {"file": ("receipt.png", io.BytesIO(png_bytes), "image/png")}

        response = client.post("/api/v1/ingest/file", files=files)
        assert response.status_code == 201

        data = response.json()
        assert data["title"] == "receipt.png"
        assert data["source_type"] == "image"
        assert "document_id" in data
        assert data["document_id"].startswith("doc_")
        assert data["character_count"] > 0
        assert data["metadata"] is not None
        assert data["metadata"]["format"] == "PNG"
        assert data["metadata"]["engine"] == "tesseract"
        assert data["metadata"]["original_filename"] == "receipt.png"

        # Check raw JSON storage
        saved_file = temp_raw_dir / f"{data['document_id']}.json"
        assert saved_file.exists()

        with open(saved_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
            assert saved_data["document_id"] == data["document_id"]
            assert saved_data["source_type"] == "image"
            assert "1024" in saved_data["content"]
            assert saved_data["metadata"]["format"] == "PNG"
    finally:
        app.dependency_overrides.clear()


def test_ingest_jpeg_with_text(temp_raw_dir):
    """Verify JPEG image text extraction via OCR."""
    test_service = IngestionService(raw_data_dir=temp_raw_dir)
    app.dependency_overrides[get_ingestion_service] = lambda: test_service

    try:
        jpg_bytes = generate_image_bytes(text="INVOICE NUMBER 2048", format="JPEG")
        files = {"file": ("bill.jpg", io.BytesIO(jpg_bytes), "image/jpeg")}

        response = client.post("/api/v1/ingest/file", files=files)
        assert response.status_code == 201

        data = response.json()
        assert data["title"] == "bill.jpg"
        assert data["source_type"] == "image"
        assert data["metadata"]["format"] == "JPEG"
        assert data["character_count"] > 0
    finally:
        app.dependency_overrides.clear()


def test_ingest_webp_with_text(temp_raw_dir):
    """Verify WEBP image text extraction via OCR."""
    test_service = IngestionService(raw_data_dir=temp_raw_dir)
    app.dependency_overrides[get_ingestion_service] = lambda: test_service

    try:
        webp_bytes = generate_image_bytes(text="INVOICE NUMBER 4096", format="WEBP")
        files = {"file": ("scan.webp", io.BytesIO(webp_bytes), "image/webp")}

        response = client.post("/api/v1/ingest/file", files=files)
        assert response.status_code == 201

        data = response.json()
        assert data["title"] == "scan.webp"
        assert data["source_type"] == "image"
        assert data["metadata"]["format"] == "WEBP"
        assert data["character_count"] > 0
    finally:
        app.dependency_overrides.clear()


def test_ingest_blank_image():
    """Verify image with no readable text is rejected with HTTP 400."""
    blank_bytes = generate_image_bytes(text=None, format="PNG")
    files = {"file": ("empty_canvas.png", io.BytesIO(blank_bytes), "image/png")}

    response = client.post("/api/v1/ingest/file", files=files)
    assert response.status_code == 400
    assert "Image contains no readable text" in response.json()["detail"]


def test_ingest_corrupted_image():
    """Verify corrupted image bytes are rejected with HTTP 400."""
    corrupted_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00corrupted-bytes-stream"
    files = {"file": ("broken.png", io.BytesIO(corrupted_bytes), "image/png")}

    response = client.post("/api/v1/ingest/file", files=files)
    assert response.status_code == 400
    assert "Corrupted or unreadable image file" in response.json()["detail"]


def test_ingest_unsupported_image_format():
    """Verify unsupported image formats (e.g. .gif, .bmp) are rejected with HTTP 400."""
    # Test extension rejection
    files = {"file": ("animation.gif", io.BytesIO(b"GIF89a..."), "image/gif")}
    response = client.post("/api/v1/ingest/file", files=files)
    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"]
