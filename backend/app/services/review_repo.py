"""Repository for review_items and responses.

This is the only module that should write SQL against those tables. Everything
above it (routers, the seed flow) calls these functions and gets back plain
Python dicts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from psycopg.types.json import Jsonb

from app.services import db, scheduler


@dataclass
class ReviewItem:
    id: UUID
    user_id: UUID
    source: str
    topic: str | None
    bloom_level: str
    question: str
    expected_answer: str
    fsrs_state: dict[str, Any]
    due_at: datetime
    last_reviewed_at: datetime | None
    created_at: datetime


def _row_to_item(row: tuple) -> ReviewItem:
    return ReviewItem(
        id=row[0],
        user_id=row[1],
        source=row[2],
        topic=row[3],
        bloom_level=row[4],
        question=row[5],
        expected_answer=row[6],
        fsrs_state=row[7],
        due_at=row[8],
        last_reviewed_at=row[9],
        created_at=row[10],
    )


_COLS = (
    "id, user_id, source, topic, bloom_level, question, expected_answer, "
    "fsrs_state, due_at, last_reviewed_at, created_at"
)
_SELECT = f"SELECT {_COLS} FROM review_items"


def create_item(
    *,
    user_id: UUID | str,
    source: str,
    topic: str | None,
    bloom_level: str,
    question: str,
    expected_answer: str,
) -> ReviewItem:
    """Create a fresh review item (due immediately, brand-new FSRS state)."""
    state = scheduler.new_card_state()
    due_at = scheduler.initial_due_at(state)

    with db.connection() as conn, conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO review_items
                (user_id, source, topic, bloom_level, question, expected_answer,
                 fsrs_state, due_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING {_COLS}
            """,
            (user_id, source, topic, bloom_level, question, expected_answer,
             Jsonb(state), due_at),
        )
        return _row_to_item(cur.fetchone())


def get_due_items(user_id: UUID | str, limit: int = 1) -> list[ReviewItem]:
    """Items where due_at <= now(), oldest-due first."""
    with db.connection() as conn, conn.cursor() as cur:
        cur.execute(
            _SELECT + " WHERE user_id = %s AND due_at <= NOW() ORDER BY due_at ASC LIMIT %s",
            (user_id, limit),
        )
        return [_row_to_item(r) for r in cur.fetchall()]


def get_item(item_id: UUID | str) -> ReviewItem | None:
    with db.connection() as conn, conn.cursor() as cur:
        cur.execute(_SELECT + " WHERE id = %s", (item_id,))
        row = cur.fetchone()
        return _row_to_item(row) if row else None


def submit_response(
    *,
    item_id: UUID | str,
    rating: int,
    response_time_ms: int | None = None,
) -> ReviewItem:
    """Apply a rating: update the item's FSRS state + due_at and log the response.

    Both writes happen in one transaction. The updated item is returned so the
    caller can show the next-due-in confirmation to the user.
    """
    with db.connection() as conn, conn.cursor() as cur:
        cur.execute(_SELECT + " WHERE id = %s FOR UPDATE", (item_id,))
        row = cur.fetchone()
        if row is None:
            raise LookupError(f"review_item {item_id} not found")
        item = _row_to_item(row)

        new_state, new_due_at = scheduler.review(item.fsrs_state, rating)

        cur.execute(
            """
            UPDATE review_items
            SET fsrs_state = %s,
                due_at = %s,
                last_reviewed_at = NOW()
            WHERE id = %s
            RETURNING last_reviewed_at
            """,
            (Jsonb(new_state), new_due_at, item.id),
        )
        last_reviewed_at = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO responses (review_item_id, rating, response_time_ms)
            VALUES (%s, %s, %s)
            """,
            (item.id, rating, response_time_ms),
        )

        return ReviewItem(
            id=item.id,
            user_id=item.user_id,
            source=item.source,
            topic=item.topic,
            bloom_level=item.bloom_level,
            question=item.question,
            expected_answer=item.expected_answer,
            fsrs_state=new_state,
            due_at=new_due_at,
            last_reviewed_at=last_reviewed_at,
            created_at=item.created_at,
        )


def get_stats(user_id: UUID | str) -> dict[str, Any]:
    """Snapshot for the dashboard: counts, streak, due-today, mastery by topic."""
    with db.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
              COUNT(*) AS total,
              COUNT(*) FILTER (WHERE due_at <= NOW()) AS due_now,
              COUNT(*) FILTER (WHERE due_at::date = CURRENT_DATE) AS due_today
            FROM review_items
            WHERE user_id = %s
            """,
            (user_id,),
        )
        total, due_now, due_today = cur.fetchone()

        cur.execute(
            """
            SELECT topic, COUNT(*), AVG((fsrs_state->>'stability')::float) FILTER (WHERE fsrs_state ? 'stability')
            FROM review_items
            WHERE user_id = %s AND topic IS NOT NULL
            GROUP BY topic
            ORDER BY topic
            """,
            (user_id,),
        )
        mastery_by_topic = [
            {
                "topic": t,
                "item_count": int(n),
                "avg_stability": round(s, 2) if s is not None else None,
            }
            for t, n, s in cur.fetchall()
        ]

        cur.execute(
            """
            SELECT COUNT(DISTINCT reviewed_at::date)
            FROM responses r
            JOIN review_items i ON i.id = r.review_item_id
            WHERE i.user_id = %s
              AND reviewed_at >= NOW() - INTERVAL '30 days'
            """,
            (user_id,),
        )
        streak_days = int(cur.fetchone()[0])

    return {
        "total_items": int(total),
        "due_now": int(due_now),
        "due_today": int(due_today),
        "streak_days": streak_days,
        "mastery_by_topic": mastery_by_topic,
    }
