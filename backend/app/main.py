import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import chat, ingest, quiz, topics, upload

app = FastAPI(
    title="AI Teaching Assistant",
    description="RAG-powered AI teacher with multi-format ingestion, chat, and quiz generation.",
    version="2.0.0",
)

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(upload.router)
app.include_router(ingest.router)
app.include_router(quiz.router)
app.include_router(topics.router)


@app.get("/api/health")
async def health():
    from app.services.vector_store import vector_store

    return {
        "status": "ok",
        "total_chunks": vector_store.total_chunks,
        "topics": vector_store.get_topics(),
    }
