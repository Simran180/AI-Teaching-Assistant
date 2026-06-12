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

from fastapi import APIRouter, HTTPException, Query, Request

from app.core.config import DEMO_USER_ID
from app.core.rate_limit import RATE_LIMIT_QUIZ, limiter
from app.models.schemas import (
    DueScope,
    ReviewDueResponse,
    ReviewItemOut,
    ReviewSeedRequest,
    ReviewSeedResponse,
    ReviewStatsResponse,
    ReviewSubmitRequest,
    ReviewSubmitResponse,
)
from app.services import review_repo
from app.services.llm import generate_review_questions, grade_answer
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
async def get_due_items(
    request: Request,
    scope: DueScope = Query(
        default="now",
        description="'now' = strictly overdue; 'today' = overdue or due before end-of-day UTC.",
    ),
    limit: int = Query(default=50, ge=1, le=200),
):
    """Return ALL review items due in the given scope, oldest-due first.

    The response also includes overall `due_now` and `due_today` counts so
    the UI can render "5 to review now / 12 today" badges without a second
    round-trip to `/stats`.
    """
    user_id = _current_user_id()
    try:
        items = review_repo.get_due_items(user_id, limit=limit, scope=scope)
        stats = review_repo.get_stats(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("review/due failed")
        raise HTTPException(status_code=500, detail=f"DB error: {exc}")

    return ReviewDueResponse(
        scope=scope,
        items=[_to_item_out(i) for i in items],
        due_now=int(stats["due_now"]),
        due_today=int(stats["due_today"]),
    )


@router.post("/submit", response_model=ReviewSubmitResponse)
@limiter.limit("60/minute")
async def submit_review(request: Request, req: ReviewSubmitRequest):
    """Record a rating, advance FSRS state, optionally grade a typed answer,
    and return the next due item.

    If the user supplied `user_answer`, we:
      1. Load the item (read-only) to get the expected answer.
      2. Run the LLM grader.
      3. Persist the answer + grade alongside the rating in `responses`.
      4. Return the grade in the response so the UI can show feedback.

    Grading is best-effort: if the LLM call fails we still record the
    rating and answer, just without a graded verdict, so the FSRS schedule
    is never blocked on a model outage.
    """
    user_id = _current_user_id()

    # If grading is requested, ownership must be verified before we even
    # call the LLM — otherwise a stranger could pay for grader calls on
    # another user's items.
    if req.user_answer:
        existing = review_repo.get_item(req.item_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="review_item not found")
        if str(existing.user_id) != str(user_id):
            raise HTTPException(status_code=403, detail="Not your review item.")

    graded = None
    if req.user_answer:
        try:
            graded = grade_answer(
                question=existing.question,
                expected_answer=existing.expected_answer,
                user_answer=req.user_answer,
            )
        except Exception as exc:
            # Best-effort: log but keep going. The user's rating still
            # drives the schedule; we just won't have an LLM verdict.
            logger.warning("submit: grader failed, continuing without grade: %s", exc)

    try:
        updated = review_repo.submit_response(
            item_id=req.item_id,
            rating=req.rating,
            response_time_ms=req.response_time_ms,
            user_answer=req.user_answer,
            is_correct=graded.is_correct if graded else None,
            grade_feedback=graded.feedback if graded else None,
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

    # Cross-user submit attempts must not leak data (covers the no-grading path).
    if str(updated.user_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Not your review item.")

    next_due = review_repo.get_due_items(user_id, limit=1, scope="now")
    next_item = _to_item_out(next_due[0]) if next_due else None

    return ReviewSubmitResponse(
        item_id=updated.id,
        next_due_at=updated.due_at,
        expected_answer=updated.expected_answer,
        next_item=next_item,
        grade=graded,
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
