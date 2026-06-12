import json
import logging

from google import genai
from google.genai import types

from app.core.config import CHAT_MODEL, GEMINI_API_KEY
from app.models.schemas import (
    AnswerGrade,
    BloomQuestion,
    BloomQuestionSet,
    QuizResponse,
)

logger = logging.getLogger(__name__)

client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPTS = {
    "beginner": (
        "You are a patient and encouraging AI teacher. Explain concepts in the simplest "
        "possible terms, using everyday analogies. Assume the student has no prior knowledge. "
        "Use short sentences and bullet points."
    ),
    "intermediate": (
        "You are a knowledgeable AI teacher. Explain concepts clearly with appropriate "
        "technical depth. Provide examples and connect ideas to broader topics."
    ),
    "advanced": (
        "You are an expert-level AI teacher. Provide rigorous, in-depth explanations with "
        "technical precision. Reference underlying theory and edge cases. Assume the student "
        "has solid foundational knowledge."
    ),
    "eli5": (
        "You are an AI teacher explaining to a 5-year-old. Use very simple words, fun "
        "analogies (toys, animals, food), and short sentences. Make it playful and engaging."
    ),
}


def build_rag_prompt(context_chunks: list[dict], question: str, mode: str) -> tuple[str, str]:
    """Build the system instruction and user message for Gemini.

    Returns (system_instruction, user_message).
    """
    system = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["intermediate"])

    context_text = "\n\n---\n\n".join(
        f"[Source: {c.get('source', 'unknown')}]\n{c['text']}" for c in context_chunks
    )

    user_message = (
        f"Use the following reference material to answer the question. "
        f"If the material doesn't cover the topic, say so and answer from your "
        f"general knowledge.\n\n"
        f"--- Reference Material ---\n{context_text}\n\n"
        f"--- Question ---\n{question}"
    )
    return system, user_message


def ask_llm(prompt_parts: tuple[str, str]) -> str:
    system_instruction, user_message = prompt_parts

    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.4,
            max_output_tokens=4000,
        ),
    )
    return response.text


def generate_quiz(context: str, num_questions: int, difficulty: str) -> str:
    """Ask the LLM to generate quiz questions as JSON (API-enforced JSON shape)."""
    system = (
        "You are a quiz generator for educational content. "
        "Each question must have exactly four options as strings starting with "
        '"A) ", "B) ", "C) ", "D) ". '
        "correct_answer must exactly match one of the four options strings."
    )
    user_msg = (
        f"Generate exactly {num_questions} multiple-choice questions at {difficulty} level "
        f"from the following material.\n\n"
        f"Material:\n{context}\n"
    )

    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=user_msg,
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.5,
            max_output_tokens=8192,
            response_mime_type="application/json",
            response_json_schema=QuizResponse.model_json_schema(),
        ),
    )
    return response.text


# ---------------------------------------------------------------------------
# Bloom-tagged question generation for spaced repetition
# ---------------------------------------------------------------------------

_REVIEW_SYSTEM_PROMPT = (
    "You are a question writer for a spaced-repetition study app. "
    "Given a single chunk of study material, write exactly THREE questions, "
    "one per Bloom's taxonomy level, in this order: recall, apply, analyze.\n\n"
    "Definitions you MUST follow:\n"
    "  - recall:  factual retrieval. Single-fact answer that appears verbatim "
    "or near-verbatim in the chunk.\n"
    "  - apply:   use the concept in a concrete scenario or worked example "
    "that is NOT given in the chunk.\n"
    "  - analyze: compare, contrast, explain why, or break the concept into "
    "parts. Requires reasoning beyond the surface text.\n\n"
    "Rules:\n"
    "  - Every answer must be supported by the chunk; do not invent facts.\n"
    "  - Keep each `expected_answer` concise (one to three sentences).\n"
    "  - Do not number questions or include the bloom level inside the "
    "question text — that field is separate.\n"
    "  - Output strictly matches the provided JSON schema."
)


def generate_review_questions(chunk_text: str) -> list[BloomQuestion]:
    """Generate three Bloom-tagged questions (recall/apply/analyze) for one chunk.

    Uses Gemini structured output so the returned JSON conforms to
    `BloomQuestionSet`. The caller is expected to handle the (rare) case
    where the model still drifts and Pydantic validation raises — we let
    the exception bubble up rather than swallowing it.
    """
    # Defensive validation: the chunk text comes from our own vector store
    # (not user input on this endpoint), but we still bound the size so a
    # rogue ingestion doesn't blow up the prompt window.
    chunk_text = (chunk_text or "").strip()
    if not chunk_text:
        raise ValueError("chunk_text must be non-empty")
    if len(chunk_text) > 8000:
        chunk_text = chunk_text[:8000]

    user_msg = (
        "Write three Bloom-tagged questions for the following chunk.\n\n"
        f"--- Chunk ---\n{chunk_text}\n"
    )

    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=user_msg,
        config=types.GenerateContentConfig(
            system_instruction=_REVIEW_SYSTEM_PROMPT,
            temperature=0.4,
            max_output_tokens=2048,
            response_mime_type="application/json",
            response_json_schema=BloomQuestionSet.model_json_schema(),
        ),
    )

    try:
        data = json.loads(response.text)
        parsed = BloomQuestionSet.model_validate(data)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.warning("generate_review_questions: invalid JSON from model: %s", exc)
        raise

    # Enforce one-of-each Bloom level so downstream code can rely on coverage.
    levels_seen = {q.bloom_level for q in parsed.questions}
    if levels_seen != {"recall", "apply", "analyze"}:
        logger.warning(
            "generate_review_questions: missing bloom levels, got %s", levels_seen
        )

    return parsed.questions


# ---------------------------------------------------------------------------
# LLM grader: compare a user's typed answer to the expected answer
# ---------------------------------------------------------------------------

_GRADER_SYSTEM_PROMPT = (
    "You are a strict but fair grader for a study app. You are given a "
    "question, the expected answer (ground truth), and the student's "
    "answer. Decide if the student's answer is substantively correct.\n\n"
    "Rules:\n"
    "  - Be generous about wording, phrasing, and minor omissions; be "
    "strict about factual accuracy and key concepts.\n"
    "  - If the student's answer contradicts the expected answer or "
    "misses a core fact, mark it incorrect.\n"
    "  - If the student is partially correct, prefer `is_correct=false` "
    "and explain what's missing in `feedback`.\n"
    "  - `feedback` must be one or two sentences directed at the student, "
    "explaining specifically what was right or wrong. Do NOT just restate "
    "the expected answer.\n"
    "  - Output must strictly match the JSON schema provided."
)


def grade_answer(
    *, question: str, expected_answer: str, user_answer: str
) -> AnswerGrade:
    """Grade a free-text answer against an expected answer.

    Returns an `AnswerGrade` (is_correct + short feedback). The LLM is
    constrained by structured output, but we still defensively re-validate
    with Pydantic to guard against schema drift.
    """
    # Validate inputs at the service boundary. The router already enforces
    # length via the request schema, but a downstream caller could skip it.
    question = (question or "").strip()
    expected_answer = (expected_answer or "").strip()
    user_answer = (user_answer or "").strip()
    if not question or not expected_answer or not user_answer:
        raise ValueError("question, expected_answer, and user_answer are required")

    # Bound each field so prompt size stays sane; the router caps user_answer
    # at 4000 chars but expected_answer can be longer.
    question = question[:1000]
    expected_answer = expected_answer[:2000]
    user_answer = user_answer[:4000]

    user_msg = (
        "Grade the student's answer to the following question.\n\n"
        f"--- Question ---\n{question}\n\n"
        f"--- Expected answer ---\n{expected_answer}\n\n"
        f"--- Student's answer ---\n{user_answer}\n"
    )

    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=user_msg,
        config=types.GenerateContentConfig(
            system_instruction=_GRADER_SYSTEM_PROMPT,
            temperature=0.1,
            max_output_tokens=512,
            response_mime_type="application/json",
            response_json_schema=AnswerGrade.model_json_schema(),
        ),
    )

    try:
        data = json.loads(response.text)
        return AnswerGrade.model_validate(data)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.warning("grade_answer: invalid JSON from model: %s", exc)
        raise
