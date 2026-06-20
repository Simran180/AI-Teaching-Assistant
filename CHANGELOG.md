# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] — 2026-06-20

### Added — Spaced-repetition review & persistent learner memory

The app now remembers what you've learned and schedules reviews so you revisit
material right before you'd forget it.

- **FSRS scheduling engine** (`services/scheduler.py`) — thin seam over the
  `fsrs` library that serializes card state to/from Postgres and translates
  Again/Hard/Good/Easy ratings into next-due dates.
- **Postgres learner state** — new `db/schema.sql` (`users`, `review_items`,
  `responses`) and a psycopg 3 connection pool in `services/db.py`.
- **Review repository** (`services/review_repo.py`) — CRUD for review items and
  responses, plus dashboard stat aggregations (due now/today, day streak,
  mastery by topic).
- **Bloom-tiered question generation** — Gemini generates recall / apply /
  analyze questions per chunk; shared seed logic lives in
  `services/review_seeder.py`.
- **Review API** (`routers/review.py`) — `POST /api/review/seed`,
  `GET /api/review/due`, `POST /api/review/submit`, `GET /api/review/stats`.
- **Auto-seed on upload/ingest** — file uploads and URL ingestion now spawn a
  background task that turns new chunks into review cards; the upload UI tells
  the user cards are being generated.
- **Review session UI** (`ReviewSession.jsx`) — flashcard flow with optional
  LLM-graded typed answers, 1–4 keyboard shortcuts, card animations, and an
  "all caught up" empty state.
- **Dashboard** (`Dashboard.jsx`) — stat cards (due now/today, total cards, day
  streak) and a mastery-by-topic bar chart; becomes the landing tab when review
  cards exist.
- **Tests** — `tests/test_scheduler.py` and `tests/test_review_repo.py`.

### Changed

- `DATABASE_URL` and `DEMO_USER_ID` environment variables added; `DATABASE_URL`
  is required for the review/dashboard features (chat, quiz, and ingestion still
  work without it).
- README updated with the spaced-repetition architecture diagram, new endpoints,
  Postgres/FSRS tech stack, setup steps, and a "how spaced repetition works"
  section.

## [0.1.0]

### Added

- RAG-powered chat over a unified multi-format ingestion pipeline (PDF, audio,
  video, image, YouTube, website) with FAISS vector storage and Gemini.
- Quiz generation, topic filtering, source attribution, and a reproducible
  retrieval eval harness in `backend/evals/`.
