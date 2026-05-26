"""Rate limiting configuration.

Uses slowapi (FastAPI-friendly wrapper around the `limits` library).
Keyed by client IP, respecting X-Forwarded-For when running behind a trusted
reverse proxy like Render. When auth lands, swap `_client_key` for one that
prefers the authenticated user id and falls back to IP for anonymous routes.
"""

from __future__ import annotations

import os

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _client_key(request: Request) -> str:
    """Prefer X-Forwarded-For (set by Render/Vercel/any sane proxy), fall back to direct IP."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


RATE_LIMIT_CHAT = os.getenv("RATE_LIMIT_CHAT", "5/minute")
RATE_LIMIT_QUIZ = os.getenv("RATE_LIMIT_QUIZ", "2/minute")
RATE_LIMIT_UPLOAD = os.getenv("RATE_LIMIT_UPLOAD", "5/minute")
RATE_LIMIT_INGEST = os.getenv("RATE_LIMIT_INGEST", "15/minute")


limiter = Limiter(key_func=_client_key)
