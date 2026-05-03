from fastapi import APIRouter

from app.models.schemas import TopicListResponse
from app.services.vector_store import vector_store

router = APIRouter(prefix="/api/topics", tags=["Topics"])


@router.get("/", response_model=TopicListResponse)
async def list_topics():
    return TopicListResponse(topics=vector_store.get_topics())
