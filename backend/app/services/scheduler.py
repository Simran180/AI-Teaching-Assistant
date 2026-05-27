"""FSRS scheduler wrapper.

The `fsrs` library does the math; this module is the seam between it and the
rest of the app. Two responsibilities:

1. Serialize / deserialize FSRS Card state to/from the JSONB column.
2. Translate our 1..4 rating ints into fsrs.Rating enum values.

Keeping this seam thin means we could swap libraries (or upgrade FSRS-6 →
FSRS-7) by editing only this file.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fsrs import Card, Rating, Scheduler

_scheduler = Scheduler()


def new_card_state() -> dict[str, Any]:
    """Return JSONB-ready state for a brand-new, never-reviewed item.

    The card is due immediately (now) so it surfaces in the first review session.
    """
    return Card().to_dict()


def review(card_state: dict[str, Any], rating: int) -> tuple[dict[str, Any], datetime]:
    """Apply a rating to a card and return (new_state, new_due_at).

    rating: 1=Again, 2=Hard, 3=Good, 4=Easy (matches FSRS Rating enum)
    """
    if rating not in (1, 2, 3, 4):
        raise ValueError(f"rating must be 1..4, got {rating}")

    card = Card.from_dict(card_state)
    new_card, _log = _scheduler.review_card(card, Rating(rating))

    due_at = new_card.due
    if isinstance(due_at, str):  # defensive — depending on lib version
        due_at = datetime.fromisoformat(due_at)
    if due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=timezone.utc)

    return new_card.to_dict(), due_at


def initial_due_at(card_state: dict[str, Any]) -> datetime:
    """Extract due timestamp from a fresh card state (always now-ish for new cards)."""
    due_raw = card_state["due"]
    if isinstance(due_raw, str):
        due = datetime.fromisoformat(due_raw)
    else:
        due = due_raw
    if due.tzinfo is None:
        due = due.replace(tzinfo=timezone.utc)
    return due
