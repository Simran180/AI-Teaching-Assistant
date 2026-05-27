"""Postgres connection pool (psycopg 3).

Single module-level pool lives for the process lifetime. Callers acquire a
connection via the `connection()` context manager — it yields a real conn,
returns it to the pool on exit, and rolls back on exception.

The pool is opened lazily on first use so importing this module never blocks
on DB connectivity (matters for the eval harness which doesn't need Postgres).
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg_pool import ConnectionPool

from app.core.config import DATABASE_URL

#lazy initialization of the connection pool, so that importing this module doesn't block on DB connectivity
_pool: ConnectionPool | None = None


def _get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL is not set. Add it to backend/.env "
                "(get a free Neon connection string at https://neon.tech)."
            )
        _pool = ConnectionPool(
            conninfo=DATABASE_URL,
            min_size=1,
            max_size=5,
            open=True,
            kwargs={"autocommit": False},
        )
    return _pool


@contextmanager
def connection() -> Iterator[psycopg.Connection]:
    """Yield a pooled connection; commit on clean exit, rollback on exception."""
    pool = _get_pool()
    with pool.connection() as conn:
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def healthcheck() -> bool:
    """True iff `SELECT 1` round-trips. Used by /api/health."""
    try:
        with connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
            return cur.fetchone() == (1,)
    except Exception:
        return False
