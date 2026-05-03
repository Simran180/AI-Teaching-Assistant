"""Unified ingestion pipeline.

Any Input → Detect Format → Extract Text → Clean → Translate → Chunk → Embed → Store
"""
import io
import logging
import re
from pathlib import Path

import pdfplumber
from deep_translator import GoogleTranslator

from app.services.chunker import chunk_text
from app.services.processors.docx_reader import extract_text_from_docx
from app.services.processors.ocr import IMAGE_EXTENSIONS, extract_text_from_image_bytes
from app.services.processors.scraper import scrape_website
from app.services.processors.transcribe import AUDIO_EXTENSIONS, VIDEO_EXTENSIONS, transcribe_from_bytes
from app.services.processors.youtube import get_youtube_transcript
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)

TEXT_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}
ALL_FILE_EXTENSIONS = TEXT_EXTENSIONS | AUDIO_EXTENSIONS | VIDEO_EXTENSIONS | IMAGE_EXTENSIONS


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------

def detect_source_type(input_source: str) -> str:
    """Classify the input as youtube, website, or a file extension category."""
    lowered = input_source.lower().strip()

    if re.search(r"(youtube\.com|youtu\.be)", lowered):
        return "youtube"
    if lowered.startswith("http://") or lowered.startswith("https://"):
        return "website"

    ext = Path(input_source).suffix.lower()
    if ext in AUDIO_EXTENSIONS:
        return "audio"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in TEXT_EXTENSIONS:
        return "text"

    return "text"


# ---------------------------------------------------------------------------
# Text extractors (by file bytes)
# ---------------------------------------------------------------------------

def _extract_pdf(file_bytes: bytes) -> str:
    parts: list[str] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                parts.append(page_text)

    text = "\n\n".join(parts)

    if not text.strip():
        text = _extract_pdf_ocr(file_bytes)

    return text


def _extract_pdf_ocr(file_bytes: bytes) -> str:
    """Fallback: convert each PDF page to an image and run OCR."""
    import pytesseract
    from PIL import Image

    parts: list[str] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            pil_image = page.to_image(resolution=300).original
            page_text = pytesseract.image_to_string(pil_image)
            if page_text and page_text.strip():
                parts.append(page_text.strip())

    return "\n\n".join(parts)


def _extract_plain_text(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8", errors="replace")


_TEXT_EXTRACTORS: dict[str, callable] = {
    ".pdf": _extract_pdf,
    ".txt": _extract_plain_text,
    ".md": _extract_plain_text,
    ".docx": extract_text_from_docx, 
}


# ---------------------------------------------------------------------------
# Language detection + translation
# ---------------------------------------------------------------------------

def _is_mostly_english(text: str) -> bool:
    """Quick heuristic: if most characters are ASCII letters, it's likely English."""
    if not text:
        return True
    ascii_letters = sum(1 for c in text if c.isascii() and c.isalpha())
    total_letters = sum(1 for c in text if c.isalpha())
    if total_letters == 0:
        return True
    return (ascii_letters / total_letters) > 0.7


def _translate_to_english(text: str) -> str:
    """Translate text to English using Google Translate via deep-translator.
    Google's free endpoint caps out around 2000 chars per request, so we
    split by line boundaries and pause briefly between requests.
    """
    import time

    MAX_CHARS = 1800
    translator = GoogleTranslator(source="auto", target="en")

    if len(text) <= MAX_CHARS:
        return translator.translate(text)

    lines = text.split("\n")
    translated_parts: list[str] = []
    current_batch = ""

    for line in lines:
        if len(current_batch) + len(line) + 1 > MAX_CHARS:
            if current_batch:
                translated_parts.append(translator.translate(current_batch))
                time.sleep(0.5)
            current_batch = line
        else:
            current_batch = f"{current_batch}\n{line}" if current_batch else line

    if current_batch:
        translated_parts.append(translator.translate(current_batch))

    return "\n".join(translated_parts)


def _ensure_english(raw_text: str) -> str:
    """Translate to English if the text appears to be in another language."""
    if _is_mostly_english(raw_text):
        return raw_text

    logger.info("Non-English content detected, translating to English via Google Translate...")
    return _translate_to_english(raw_text)


# ---------------------------------------------------------------------------
# Cleaning
# ---------------------------------------------------------------------------

def _clean_text(text: str) -> str:
    """Normalize whitespace and remove non-printable characters."""
    text = re.sub(r"[^\S\n]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ingest_file(file_bytes: bytes, filename: str, topic: str = "General") -> int:
    """Ingest an uploaded file (any supported type).
    Extracts text, translates if needed, chunks, embeds, and stores.
    Returns the number of chunks created.
    """
    source_type = detect_source_type(filename)
    ext = Path(filename).suffix.lower()

    if source_type in ("audio", "video"):
        raw_text = transcribe_from_bytes(file_bytes, filename)
    elif source_type == "image":
        raw_text = extract_text_from_image_bytes(file_bytes)
    elif source_type == "text":
        extractor = _TEXT_EXTRACTORS.get(ext)
        if extractor is None:
            raise ValueError(
                f"Unsupported file type: {ext}. "
                f"Supported: {sorted(ALL_FILE_EXTENSIONS)}"
            )
        raw_text = extractor(file_bytes)
    else:
        raise ValueError(f"Cannot process file type '{ext}' via file upload.")

    raw_text = _clean_text(raw_text)
    print(raw_text)
    if not raw_text:
        raise ValueError("No text content could be extracted from the file.")

    raw_text = _ensure_english(raw_text)

    chunks = chunk_text(raw_text)
    return vector_store.add_chunks(chunks, source=filename, topic=topic)


def ingest_url(url: str, topic: str = "General") -> tuple[int, str]:
    """Ingest a URL (YouTube video or website).
    Returns (chunks_created, source_label).
    """
    source_type = detect_source_type(url)

    if source_type == "youtube":
        raw_text = get_youtube_transcript(url)
        source_label = f"youtube:{url}"
    elif source_type == "website":
        raw_text = scrape_website(url)
        source_label = url
    else:
        raise ValueError("URL must be a YouTube video link or a website URL.")

    raw_text = _clean_text(raw_text)
    raw_text = _ensure_english(raw_text)
    # print(raw_text)
    if not raw_text:
        raise ValueError("No text content could be extracted from the URL.")


    chunks = chunk_text(raw_text)
    print("chunks:",len(chunks))
    num_stored = vector_store.add_chunks(chunks, source=source_label, topic=topic)
    return num_stored, source_label
