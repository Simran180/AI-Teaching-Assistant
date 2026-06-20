"""Unit tests for the FSRS scheduler seam (services/scheduler.py).

Pure — no database, no network. These pin the contract the rest of the app
relies on: new-card state is JSONB-ready and due now, ratings move the due
date in the right direction, and the 1..4 rating maps to FSRS correctly.

We deliberately assert *invariants* (ordering, sign, serializability) rather
than exact day counts: FSRS intervals depend on elapsed time and library
version, so hardcoding "Good == 3 days" would be brittle. The invariants are
what the product actually depends on.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from app.services import scheduler


def _days_from_now(due: datetime) -> float:
    return (due - datetime.now(timezone.utc)).total_seconds() / 86400.0


# --- new_card_state / initial_due_at -------------------------------------

def test_new_card_state_is_jsonb_ready():
    state = scheduler.new_card_state()
    # Must survive a JSONB round-trip (it's stored in a JSONB column verbatim).
    dumped = json.dumps(state)
    assert json.loads(dumped) == state
    # Carries the fields the repo + stats queries rely on.
    assert "due" in state
    assert "stability" in state
    assert "difficulty" in state


def test_initial_due_is_now_ish_and_tz_aware():
    state = scheduler.new_card_state()
    due = scheduler.initial_due_at(state)
    assert due.tzinfo is not None, "due_at must be timezone-aware for Postgres TIMESTAMPTZ"
    # A brand-new card is due immediately so it surfaces in the first session.
    assert _days_from_now(due) < 0.01


# --- review(): rating validation -----------------------------------------

@pytest.mark.parametrize("bad_rating", [0, 5, -1, 100])
def test_review_rejects_out_of_range_rating(bad_rating):
    state = scheduler.new_card_state()
    with pytest.raises(ValueError):
        scheduler.review(state, bad_rating)


@pytest.mark.parametrize("rating", [1, 2, 3, 4])
def test_review_accepts_valid_ratings_and_returns_tz_aware_due(rating):
    state = scheduler.new_card_state()
    new_state, due = scheduler.review(state, rating)
    assert isinstance(new_state, dict)
    assert json.dumps(new_state)  # still JSONB-ready after a review
    assert due.tzinfo is not None


# --- review(): scheduling behavior ----------------------------------------

def _graduate(state):
    """Push a fresh card out of the learning steps so interval ordering is meaningful."""
    for _ in range(3):
        state, _ = scheduler.review(state, 3)  # Good
    return state


def test_rating_intervals_are_monotonic():
    """Again <= Hard <= Good <= Easy — the core FSRS guarantee the UI sells."""
    graduated = _graduate(scheduler.new_card_state())
    dues = {}
    for rating in (1, 2, 3, 4):
        _, due = scheduler.review(graduated, rating)
        dues[rating] = _days_from_now(due)
    assert dues[1] <= dues[2] <= dues[3] <= dues[4], dues


def test_again_keeps_item_short_term():
    """A failed review (Again) reschedules the item within a day."""
    graduated = _graduate(scheduler.new_card_state())
    _, due = scheduler.review(graduated, 1)  # Again
    assert _days_from_now(due) < 1.0


def test_good_eventually_schedules_days_out():
    """A graduated card rated Good is pushed at least a day into the future."""
    graduated = _graduate(scheduler.new_card_state())
    _, due = scheduler.review(graduated, 3)  # Good
    assert _days_from_now(due) >= 1.0


def test_review_does_not_mutate_input_state():
    """review() must return new state, not mutate the dict it was handed —
    the caller still holds the pre-review state until the DB write commits."""
    state = scheduler.new_card_state()
    snapshot = json.loads(json.dumps(state))
    scheduler.review(state, 3)
    assert state == snapshot
