from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    topic: str | None = None
    mode: str = Field(default="intermediate", pattern=r"^(beginner|intermediate|advanced|eli5)$")


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict]


class QuizRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=200)
    num_questions: int = Field(default=5, ge=1, le=20)
    difficulty: str = Field(default="intermediate", pattern=r"^(beginner|intermediate|advanced)$")


class QuizQuestion(BaseModel):
    question: str
    options: list[str]
    correct_answer: str
    explanation: str


class QuizResponse(BaseModel):
    questions: list[QuizQuestion]


class UploadResponse(BaseModel):
    message: str
    filename: str
    chunks_created: int
    source_type: str = ""


class IngestURLRequest(BaseModel):
    url: str = Field(..., min_length=5, max_length=2000)
    topic: str = Field(default="General", max_length=200)


class IngestURLResponse(BaseModel):
    message: str
    source: str
    source_type: str
    chunks_created: int


class TopicListResponse(BaseModel):
    topics: list[str]


# ---------------------------------------------------------------------------
# Spaced-repetition (review) schemas
# ---------------------------------------------------------------------------

BloomLevel = Literal["recall", "apply", "analyze"]


class BloomQuestion(BaseModel):
    """One Bloom-tagged question generated from a single chunk by the LLM."""

    bloom_level: BloomLevel
    question: str = Field(..., min_length=4)
    expected_answer: str = Field(..., min_length=1)


class BloomQuestionSet(BaseModel):
    """Structured-output target for `generate_review_questions`.

    Exactly three questions per chunk, one per Bloom level.
    """

    questions: list[BloomQuestion] = Field(..., min_length=3, max_length=3)


class ReviewSeedRequest(BaseModel):
    """Seed N review items for a given source/topic from indexed chunks."""

    source: str | None = Field(default=None, max_length=200)
    topic: str | None = Field(default=None, max_length=200)
    max_chunks: int = Field(default=5, ge=1, le=20)


class ReviewSeedResponse(BaseModel):
    items_created: int
    chunks_used: int
    source: str | None
    topic: str | None


class ReviewItemOut(BaseModel):
    """The shape we hand back to the client for a review item.

    We intentionally do NOT expose `expected_answer` on the due item — that
    would be the answer key. Clients can fetch it after a submit if needed.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source: str
    topic: str | None
    bloom_level: BloomLevel
    question: str
    due_at: datetime
    last_reviewed_at: datetime | None = None


class ReviewDueResponse(BaseModel):
    item: ReviewItemOut | None
    due_count: int


class ReviewSubmitRequest(BaseModel):
    item_id: UUID
    rating: int = Field(..., ge=1, le=4, description="1=Again 2=Hard 3=Good 4=Easy")
    response_time_ms: int | None = Field(default=None, ge=0, le=10 * 60 * 1000)


class ReviewSubmitResponse(BaseModel):
    """After a rating: tell the client when this item is next due, and hand
    them the next due item (if any) so the UI can chain straight into it."""

    item_id: UUID
    next_due_at: datetime
    expected_answer: str
    next_item: ReviewItemOut | None


class MasteryByTopic(BaseModel):
    topic: str
    item_count: int
    avg_stability: float | None


class ReviewStatsResponse(BaseModel):
    total_items: int
    due_now: int
    due_today: int
    streak_days: int
    mastery_by_topic: list[MasteryByTopic]
