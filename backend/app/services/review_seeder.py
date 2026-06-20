"""Turn indexed chunks into spaced-repetition review items.

This is the seam shared by two callers:
  - the manual `POST /api/review/seed` endpoint, and
  - the auto-seed background task that fires after every upload/ingest.

Keeping the chunk -> questions -> rows loop here (rather than in the router)
means both paths behave identically and there's one place to tune behavior.

The whole thing is best-effort: a chunk whose question generation fails (e.g.
the LLM is down or no API key is configured) is logged and skipped, never
raised. That matters most for the background path — auto-seed must never be
able to fail an otherwise-successful upload.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.services import review_repo
from app.services.llm import generate_review_questions
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)

# Bound the LLM fan-out per seed call. One upload can produce many chunks;
# seeding all of them would be slow and costly. If a source has more, we seed
# the first N and log the rest as skipped (no silent truncation).
AUTO_SEED_MAX_CHUNKS = 20


def seed_for_source(
    *,
    user_id: UUID | str,
    source: str | None = None,
    topic: str | None = None,
    max_chunks: int = AUTO_SEED_MAX_CHUNKS,
) -> dict[str, Any]:
    """Generate Bloom-tagged review items for chunks matching source/topic.

    Returns a summary dict: how many items were created, how many chunks were
    successfully turned into questions, and how many chunks matched in total
    (so callers can distinguish "nothing matched" from "LLM produced nothing").
    """
    chunks = vector_store.get_chunks(source=source, topic=topic, limit=max_chunks)
    available = len(chunks)

    items_created = 0
    chunks_used = 0
    for chunk in chunks:
        try:
            questions = generate_review_questions(chunk["text"])
        except Exception as exc:
            # One bad chunk shouldn't kill the whole seed. Log and continue.
            logger.warning(
                "seed: question gen failed for source=%s: %s",
                chunk.get("source"), exc,
            )
            continue

        chunks_used += 1
        for q in questions:
            try:
                review_repo.create_item(
                    user_id=user_id,
                    source=chunk["source"],
                    topic=chunk.get("topic") or None,
                    bloom_level=q.bloom_level,
                    question=q.question,
                    expected_answer=q.expected_answer,
                )
                items_created += 1
            except Exception as exc:
                logger.exception("seed: failed to persist review item: %s", exc)

    return {
        "items_created": items_created,
        "chunks_used": chunks_used,
        "chunks_available": available,
    }


def auto_seed(*, user_id: UUID | str, source: str, topic: str | None = None) -> None:
    """Fire-and-forget seeding for freshly ingested material.

    Designed to run as a FastAPI BackgroundTask. Swallows everything: a failure
    here must never surface to the user whose upload already succeeded.
    """
    try:
        result = seed_for_source(user_id=user_id, source=source, topic=topic)
        logger.info(
            "auto-seed source=%s: created %d items from %d/%d chunks",
            source, result["items_created"], result["chunks_used"],
            result["chunks_available"],
        )
    except Exception:
        logger.exception("auto-seed failed for source=%s", source)
