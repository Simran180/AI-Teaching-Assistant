from fastapi import APIRouter, HTTPException, Request

from app.core.config import TOP_K
from app.core.rate_limit import RATE_LIMIT_CHAT, limiter
from app.models.schemas import ChatRequest, ChatResponse
from app.services.llm import ask_llm, build_rag_prompt
from app.services.vector_store import vector_store

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("/", response_model=ChatResponse)
@limiter.limit(RATE_LIMIT_CHAT)
async def chat(request: Request, req: ChatRequest):
    try:
        results = vector_store.search(req.question, top_k=TOP_K, topic=req.topic)
        prompt_parts = build_rag_prompt(results, req.question, req.mode)
        answer = ask_llm(prompt_parts)

        sources = [
            {"source": r["source"], "topic": r["topic"], "score": round(r["score"], 3)}
            for r in results
        ]

        return ChatResponse(answer=answer, sources=sources)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
