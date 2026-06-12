"""Spaced-repetition review endpoints.

Four endpoints stitched on top of:
  - `services.vector_store` (source of chunks to turn into questions)
  - `services.llm.generate_review_questions` (Bloom-tagged question gen)
  - `services.review_repo` (Postgres CRUD for review_items + responses)
  - `services.scheduler` (FSRS state transitions, via review_repo)

The demo-user model: every request is implicitly authenticated as
`DEMO_USER_ID` until real auth lands. Centralizing that lookup here means
swapping in real auth later touches only `_current_user_id`.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from app.core.config import DEMO_USER_ID
from app.core.rate_limit import RATE_LIMIT_QUIZ, limiter
from app.models.schemas import (
    ReviewDueResponse,
    ReviewItemOut,
    ReviewSeedRequest,
    ReviewSeedResponse,
    ReviewStatsResponse,
    ReviewSubmitRequest,
    ReviewSubmitResponse,
)
from app.services import review_repo
from app.services.llm import generate_review_questions
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/review", tags=["Review"])


def _current_user_id() -> str:
    """Resolve the acting user. Single-user demo mode for now."""
    return DEMO_USER_ID


def _to_item_out(item: review_repo.ReviewItem) -> ReviewItemOut:
    return ReviewItemOut(
        id=item.id,
        source=item.source,
        topic=item.topic,
        bloom_level=item.bloom_level,
        question=item.question,
        due_at=item.due_at,
        last_reviewed_at=item.last_reviewed_at,
    )


@router.post("/seed", response_model=ReviewSeedResponse)
@limiter.limit(RATE_LIMIT_QUIZ)
async def seed_review_items(request: Request, req: ReviewSeedRequest):
    """Generate Bloom-tagged review items from indexed chunks.

    Pulls up to `max_chunks` chunks matching the given source and/or topic
    from the vector store, asks the LLM for 3 Bloom-level questions per
    chunk, and persists each as a `review_items` row due immediately.
    """
    if not req.source and not req.topic:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one of `source` or `topic` to seed from.",
        )

    chunks = vector_store.get_chunks(
        source=req.source,
        topic=req.topic,
        limit=req.max_chunks,
    )
    if not chunks:
        raise HTTPException(
            status_code=404,
            detail=(
                "No indexed chunks match the given source/topic. "
                "Upload or ingest material first."
            ),
        )

    user_id = _current_user_id()
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

    if items_created == 0:
        raise HTTPException(
            status_code=502,
            detail="Failed to generate any review questions. Try again.",
        )

    return ReviewSeedResponse(
        items_created=items_created,
        chunks_used=chunks_used,
        source=req.source,
        topic=req.topic,
    )


@router.get("/due", response_model=ReviewDueResponse)
async def get_due_item(request: Request):
    """Return the next-due review item for the current user (oldest-due first)."""
    user_id = _current_user_id()
    try:
        due = review_repo.get_due_items(user_id, limit=1)
        # We also want the total due-count so the UI can show "X to review".
        stats = review_repo.get_stats(user_id)
    except Exception as exc:
        logger.exception("review/due failed")
        raise HTTPException(status_code=500, detail=f"DB error: {exc}")

    item = _to_item_out(due[0]) if due else None
    return ReviewDueResponse(item=item, due_count=int(stats["due_now"]))


@router.post("/submit", response_model=ReviewSubmitResponse)
@limiter.limit("60/minute")
async def submit_review(request: Request, req: ReviewSubmitRequest):
    """Record a rating, advance FSRS state, return the next due item (if any)."""
    user_id = _current_user_id()
    try:
        updated = review_repo.submit_response(
            item_id=req.item_id,
            rating=req.rating,
            response_time_ms=req.response_time_ms,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        # scheduler raises this for out-of-range ratings; Pydantic already
        # catches them, but keep the safety net for direct service callers.
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("review/submit failed")
        raise HTTPException(status_code=500, detail=f"DB error: {exc}")

    # Cross-user submit attempts must not leak data.
    if str(updated.user_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Not your review item.")

    next_due = review_repo.get_due_items(user_id, limit=1)
    next_item = _to_item_out(next_due[0]) if next_due else None

    return ReviewSubmitResponse(
        item_id=updated.id,
        next_due_at=updated.due_at,
        expected_answer=updated.expected_answer,
        next_item=next_item,
    )


@router.get("/stats", response_model=ReviewStatsResponse)
async def review_stats(request: Request):
    """Snapshot for the dashboard."""
    user_id = _current_user_id()
    try:
        stats = review_repo.get_stats(user_id)
    except Exception as exc:
        logger.exception("review/stats failed")
        raise HTTPException(status_code=500, detail=f"DB error: {exc}")

    return ReviewStatsResponse(**stats)
