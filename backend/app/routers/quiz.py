import json

from fastapi import APIRouter, HTTPException

from app.core.config import TOP_K
from app.models.schemas import QuizRequest, QuizResponse
from app.services.llm import generate_quiz
from app.services.vector_store import vector_store

router = APIRouter(prefix="/api/quiz", tags=["Quiz"])


@router.post("/", response_model=QuizResponse)
async def create_quiz(req: QuizRequest):
    results = vector_store.search(req.topic, top_k=TOP_K * 2, topic=None)
    if not results:
        raise HTTPException(status_code=404, detail="No content found for this topic. Upload material first.")

    context = "\n\n".join(r["text"] for r in results)
    raw = generate_quiz(context, req.num_questions, req.difficulty)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="LLM returned invalid quiz format. Please try again.")

    return QuizResponse(**data)
