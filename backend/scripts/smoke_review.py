"""End-to-end smoke test for the review API (Sprint 2 deliverable).

Drives the real FastAPI app in-process via httpx's ASGI transport — no server
to start, no curl, but it exercises the exact same routing, Pydantic
validation, and DB path a real client hits:

    seed  ->  GET /due  ->  POST /submit  ->  GET /stats

Two seeding paths:
  * If GEMINI_API_KEY is real AND chunks are indexed, it calls the live
    POST /api/review/seed (LLM-generated Bloom questions) — the full flow.
  * Otherwise it seeds a few synthetic items directly via review_repo so the
    rest of the HTTP flow (due/submit/stats) is still proven. The LLM is an
    external dependency, not part of what this script verifies.

All items created here are deleted on exit. Run from the backend/ dir:

    ../venv/bin/python -m scripts.smoke_review
"""

from __future__ import annotations

import asyncio
import os
import sys

# A non-empty key lets the app import (the genai client constructs lazily and
# makes no network call until something actually generates). We only hit the
# live LLM if the key looks real.
_REAL_KEY = bool(os.getenv("GEMINI_API_KEY", "").strip())
os.environ.setdefault("GEMINI_API_KEY", "dummy-smoke-key")

import httpx  # noqa: E402

from app.core.config import DEMO_USER_ID  # noqa: E402
from app.main import app  # noqa: E402
from app.services import db, review_repo  # noqa: E402
from app.services.vector_store import vector_store  # noqa: E402

SMOKE_SOURCE = "__smoke_review__"

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"


def _check(label: str, ok: bool, detail: str = "") -> bool:
    print(f"  [{PASS if ok else FAIL}] {label}" + (f" — {detail}" if detail else ""))
    return ok


def _seed_synthetic(n: int = 3) -> int:
    """Create n review items without the LLM. Returns count created."""
    levels = ["recall", "apply", "analyze"]
    for i in range(n):
        review_repo.create_item(
            user_id=DEMO_USER_ID,
            source=SMOKE_SOURCE,
            topic="__smoke_topic__",
            bloom_level=levels[i % 3],
            question=f"[smoke] question #{i + 1}: what is {i} + {i}?",
            expected_answer=str(i + i),
        )
    return n


def _cleanup() -> None:
    with db.connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM review_items WHERE source = %s", (SMOKE_SOURCE,))


async def run() -> bool:
    if not db.healthcheck():
        print("DB unreachable — set DATABASE_URL in backend/.env. Aborting.")
        return False

    transport = httpx.ASGITransport(app=app)
    results: list[bool] = []

    async with httpx.AsyncClient(transport=transport, base_url="http://smoke") as c:
        # --- SEED -----------------------------------------------------------
        print("\n1. SEED")
        seeded_via_llm = False
        chunks = vector_store.get_chunks(limit=1)
        if _REAL_KEY and chunks:
            src = chunks[0]["source"]
            r = await c.post("/api/review/seed", json={"source": src, "max_chunks": 1})
            seeded_via_llm = r.status_code == 200
            results.append(_check(
                f"POST /seed (live LLM, source={src!r})",
                seeded_via_llm,
                f"HTTP {r.status_code}; {r.json() if r.status_code == 200 else r.text[:120]}",
            ))
        if not seeded_via_llm:
            reason = "no GEMINI_API_KEY" if not _REAL_KEY else "no indexed chunks"
            n = _seed_synthetic(3)
            print(f"  (live seed skipped: {reason} — seeded {n} synthetic items instead)")

        # --- DUE ------------------------------------------------------------
        print("\n2. GET /due")
        r = await c.get("/api/review/due", params={"scope": "now", "limit": 50})
        due_ok = r.status_code == 200 and len(r.json().get("items", [])) > 0
        body = r.json() if r.status_code == 200 else {}
        results.append(_check(
            "returns at least one due item",
            due_ok,
            f"HTTP {r.status_code}; due_now={body.get('due_now')} items={len(body.get('items', []))}",
        ))
        # The answer key must NOT leak on the due item.
        if due_ok:
            first = body["items"][0]
            results.append(_check(
                "due item hides expected_answer (no answer-key leak)",
                "expected_answer" not in first,
            ))
            target_id = first["id"]
            target_due = first["due_at"]
        else:
            print("  cannot continue without a due item.")
            return all(results) and bool(results)

        # --- SUBMIT ---------------------------------------------------------
        print("\n3. POST /submit (rating=Good)")
        r = await c.post("/api/review/submit", json={"item_id": target_id, "rating": 3})
        sub_ok = r.status_code == 200
        sub = r.json() if sub_ok else {}
        results.append(_check("submit accepted", sub_ok, f"HTTP {r.status_code}"))
        if sub_ok:
            results.append(_check(
                "FSRS pushed due_at into the future",
                sub["next_due_at"] > target_due,
                f"{target_due} -> {sub['next_due_at']}",
            ))
            results.append(_check(
                "response exposes expected_answer after grading",
                bool(sub.get("expected_answer")),
            ))
            results.append(_check(
                "submitted item no longer first in the due queue",
                (sub.get("next_item") or {}).get("id") != target_id,
            ))

        # --- STATS ----------------------------------------------------------
        print("\n4. GET /stats")
        r = await c.get("/api/review/stats")
        stats = r.json() if r.status_code == 200 else {}
        stats_ok = r.status_code == 200 and {
            "total_items", "due_now", "due_today", "streak_days", "mastery_by_topic"
        } <= set(stats)
        results.append(_check(
            "stats snapshot has all dashboard fields",
            stats_ok,
            f"total={stats.get('total_items')} streak={stats.get('streak_days')}",
        ))

    return all(results) and bool(results)


def main() -> int:
    try:
        ok = asyncio.run(run())
    finally:
        _cleanup()
    print("\n" + ("SMOKE TEST PASSED ✅" if ok else "SMOKE TEST FAILED ❌"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
