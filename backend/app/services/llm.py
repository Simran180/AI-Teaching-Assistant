from google import genai
from google.genai import types

from app.core.config import CHAT_MODEL, GEMINI_API_KEY

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
    """Ask the LLM to generate quiz questions as JSON."""
    system = (
        "You are a quiz generator for educational content. "
        "Return ONLY valid JSON — no markdown, no code fences, no explanation."
    )
    user_msg = (
        f"Generate exactly {num_questions} multiple-choice questions at {difficulty} level "
        f"from the following material.\n\n"
        f"Material:\n{context}\n\n"
        f"Return a JSON object with this exact schema:\n"
        f'{{"questions": [\n'
        f'  {{"question": "...", "options": ["A) ...", "B) ...", "C) ...", "D) ..."], '
        f'"correct_answer": "A) ...", "explanation": "..."}}\n'
        f"]}}"
    )

    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=user_msg,
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.7,
            max_output_tokens=3000,
        ),
    )
    return response.text
