"""Website content extraction using requests + BeautifulSoup."""
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

TIMEOUT = 15
ALLOWED_SCHEMES = {"http", "https"}


def validate_url(url: str) -> str:
    """Basic URL validation — only allow http(s) schemes."""
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError(f"Invalid URL scheme: '{parsed.scheme}'. Only HTTP/HTTPS allowed.")
    if not parsed.netloc:
        raise ValueError("Invalid URL: no host found.")
    return url


def scrape_website(url: str) -> str:
    """Fetch a webpage and extract its readable text content."""
    url = validate_url(url)
    resp = requests.get(
        url,
        timeout=TIMEOUT,
        headers={"User-Agent": "AI-Teaching-Assistant/1.0"},
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    return _clean_scraped_text(text)


def _clean_scraped_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if len(line) > 2]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
