"""Integration tests for services/review_repo.py against the live Postgres.

These exercise the full create -> read -> update path the plan's Sprint 1
deliverable calls for ("can insert/read/update review_items"), including the
FSRS state transition and the audit row in `responses`.

Skipped automatically when the database is unreachable, so the suite still
passes in environments without a DATABASE_URL. Every test cleans up the rows
it creates (responses cascade-delete with the item).
"""

from __future__ import annotations

import pytest

from app.core.config import DEMO_USER_ID
from app.services import db, review_repo

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _require_db(db_available):
    if not db_available:
        pytest.skip("Postgres not reachable — set DATABASE_URL in backend/.env")


@pytest.fixture
def item():
    """Create a throwaway review item and guarantee it's deleted afterward."""
    created = review_repo.create_item(
        user_id=DEMO_USER_ID,
        source="__pytest__",
        topic="__pytest_topic__",
        bloom_level="recall",
        question="What is 2 + 2?",
        expected_answer="4",
    )
    try:
        yield created
    finally:
        with db.connection() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM review_items WHERE id = %s", (created.id,))


def test_create_item_is_due_immediately(item):
    assert item.id is not None
    assert item.bloom_level == "recall"
    assert item.question == "What is 2 + 2?"
    assert item.last_reviewed_at is None
    assert "stability" in item.fsrs_state  # full FSRS card persisted


def test_created_item_is_readable(item):
    fetched = review_repo.get_item(item.id)
    assert fetched is not None
    assert fetched.id == item.id
    assert fetched.expected_answer == "4"


def test_new_item_shows_up_in_due_queue(item):
    due = review_repo.get_due_items(DEMO_USER_ID, limit=200, scope="now")
    assert any(i.id == item.id for i in due), "freshly created item should be due now"


def test_submit_advances_due_and_logs_response(item):
    updated = review_repo.submit_response(
        item_id=item.id,
        rating=3,  # Good
        response_time_ms=1500,
    )
    # FSRS pushed the due date forward and stamped the review time.
    assert updated.due_at > item.due_at
    assert updated.last_reviewed_at is not None
    assert updated.fsrs_state != item.fsrs_state

    # An audit row landed in `responses`.
    with db.connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT rating, response_time_ms FROM responses WHERE review_item_id = %s",
            (item.id,),
        )
        rows = cur.fetchall()
    assert rows == [(3, 1500)]


def test_submit_rejects_unknown_item():
    # A random UUID that does not exist must raise, not silently no-op.
    with pytest.raises(LookupError):
        review_repo.submit_response(
            item_id="00000000-0000-0000-0000-0000000000ff",
            rating=3,
        )


def test_stats_shape(item):
    stats = review_repo.get_stats(DEMO_USER_ID)
    assert set(stats) >= {
        "total_items",
        "due_now",
        "due_today",
        "streak_days",
        "mastery_by_topic",
    }
    assert stats["total_items"] >= 1
    assert isinstance(stats["mastery_by_topic"], list)
