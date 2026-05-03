"""Image text extraction using pytesseract OCR."""
import io
import re

import pytesseract
from PIL import Image

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}


def extract_text_from_image_bytes(file_bytes: bytes) -> str:
    """Run OCR on image bytes and return cleaned text."""
    image = Image.open(io.BytesIO(file_bytes))
    raw = pytesseract.image_to_string(image)
    return _clean_ocr_text(raw)


def _clean_ocr_text(text: str) -> str:
    """Remove excessive whitespace and junk characters from OCR output."""
    text = re.sub(r"[^\S\n]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
