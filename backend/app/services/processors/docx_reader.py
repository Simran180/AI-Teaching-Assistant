"""DOCX file text extraction."""
import io

import docx


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract all paragraph text from a .docx file."""
    document = docx.Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)
