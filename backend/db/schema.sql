-- AI Teaching Assistant — spaced-repetition schema.
-- Apply once: psql "$DATABASE_URL" -f backend/db/schema.sql
-- Idempotent — safe to re-run.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- for gen_random_uuid()

CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS review_items (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source            TEXT NOT NULL,        -- e.g. "photosynthesis" — matches FAISS source
    topic             TEXT,                 -- e.g. "Biology"
    bloom_level       TEXT NOT NULL CHECK (bloom_level IN ('recall', 'apply', 'analyze')),
    question          TEXT NOT NULL,
    expected_answer   TEXT NOT NULL,
    fsrs_state        JSONB NOT NULL,       -- full Card.to_dict() — owned by services/scheduler.py
    due_at            TIMESTAMPTZ NOT NULL, -- denormalized from fsrs_state.due for indexing
    last_reviewed_at  TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- The core hot query: "next due item for user X". Composite index makes it cheap.
CREATE INDEX IF NOT EXISTS idx_review_items_user_due
    ON review_items (user_id, due_at);

CREATE TABLE IF NOT EXISTS responses (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_item_id    UUID NOT NULL REFERENCES review_items(id) ON DELETE CASCADE,
    rating            SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 4),  -- 1=Again 2=Hard 3=Good 4=Easy
    response_time_ms  INTEGER,
    reviewed_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Captured when the user types an answer (active-recall flow); nullable
    -- so the legacy Anki-style self-rating flow still works.
    user_answer       TEXT,
    -- LLM-graded correctness + short feedback. Both null when the user did
    -- not provide a typed answer (no grading performed).
    is_correct        BOOLEAN,
    grade_feedback    TEXT
);

CREATE INDEX IF NOT EXISTS idx_responses_item
    ON responses (review_item_id, reviewed_at);

-- Idempotent column additions for already-deployed databases.
ALTER TABLE responses ADD COLUMN IF NOT EXISTS user_answer    TEXT;
ALTER TABLE responses ADD COLUMN IF NOT EXISTS is_correct     BOOLEAN;
ALTER TABLE responses ADD COLUMN IF NOT EXISTS grade_feedback TEXT;

-- Seed the demo user (matches DEMO_USER_ID in config.py).
INSERT INTO users (id, email)
VALUES ('00000000-0000-0000-0000-000000000001', 'demo@example.com')
ON CONFLICT (id) DO NOTHING;
