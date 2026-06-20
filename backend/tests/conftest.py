"""Shared pytest fixtures and path setup.

Tests import the app as `app.services...`. Putting the backend dir on
sys.path here means `pytest` works whether invoked from the repo root or
from `backend/`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture(scope="session")
def db_available() -> bool:
    """True iff the live Postgres is reachable. Integration tests skip if not."""
    from app.services import db

    return db.healthcheck()
