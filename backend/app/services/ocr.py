import io
import logging
from typing import Any, Dict, Optional, Tuple

from PIL import Image, UnidentifiedImageError
import pytesseract
from pytesseract import TesseractError, TesseractNotFoundError

from app.core.config import OCRConfig, settings

logger = logging.getLogger("rag-backend.ocr")

SUPPORTED_IMAGE_FORMATS = {"PNG", "JPEG", "JPG", "WEBP"}
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


class OCRService:
    """Configurable OCR service supporting Tesseract and future pluggable engines."""

    def __init__(self, config: Optional[OCRConfig] = None):
        self.config = config or settings.rag.ocr
        # Configure tesseract binary path if provided in config or env
        tess_cmd = self.config.tesseract_cmd or settings.tesseract_cmd
        if tess_cmd:
            pytesseract.pytesseract.tesseract_cmd = tess_cmd

    def extract_text_from_image(
        self,
        image_bytes: bytes,
        filename: Optional[str] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """Validate image, run OCR text extraction, and return raw text and metadata."""
        if not image_bytes or len(image_bytes) == 0:
            raise ValueError("Uploaded image file is empty.")

        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                img_format = (img.format or "").upper()
                # Normalize JPEG/JPG
                if img_format not in SUPPORTED_IMAGE_FORMATS:
                    raise ValueError(
                        f"Unsupported image format '{img_format or 'UNKNOWN'}'. "
                        "Only PNG, JPG/JPEG, and WEBP formats are supported."
                    )

                width, height = img.size

                # Convert palette/alpha modes to RGB for OCR compatibility
                if img.mode in ("RGBA", "LA", "P"):
                    rgb_img = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img_converted = img.convert("RGBA")
                        rgb_img.paste(img_converted, mask=img_converted.split()[3])
                    else:
                        rgb_img.paste(img, mask=img.split()[-1])
                    ocr_target = rgb_img
                elif img.mode != "RGB":
                    ocr_target = img.convert("RGB")
                else:
                    ocr_target = img

                # Execute OCR extraction based on engine
                if self.config.engine.lower() == "tesseract":
                    try:
                        raw_text = pytesseract.image_to_string(
                            ocr_target,
                            lang=self.config.language,
                        )
                    except TesseractNotFoundError as e:
                        logger.error("Tesseract binary not found: %s", e)
                        raise RuntimeError("OCR engine binary is not installed or configured on the server.") from e
                    except TesseractError as e:
                        logger.error("Tesseract OCR extraction failed: %s", e)
                        raise ValueError(f"Failed to extract text from image: {str(e)}") from e
                else:
                    raise ValueError(f"Unsupported OCR engine '{self.config.engine}'. Supported engines: ['tesseract'].")

                metadata = {
                    "engine": self.config.engine,
                    "format": img_format,
                    "width": width,
                    "height": height,
                    "original_filename": filename,
                }

                return raw_text, metadata

        except (UnidentifiedImageError, OSError, IOError) as e:
            raise ValueError("Corrupted or unreadable image file.") from e
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Corrupted or unreadable image file: {str(e)}") from e


def get_ocr_service() -> OCRService:
    """Dependency provider for OCRService."""
    return OCRService()
