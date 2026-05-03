from pydantic import BaseModel, Field

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
