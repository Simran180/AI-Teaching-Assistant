from fastapi import APIRouter, HTTPException, Request

from app.core.rate_limit import RATE_LIMIT_INGEST, limiter
from app.models.schemas import IngestURLRequest, IngestURLResponse
from app.services.ingestion import detect_source_type, ingest_url

router = APIRouter(prefix="/api/ingest", tags=["Ingest"])


@router.post("/url", response_model=IngestURLResponse)
@limiter.limit(RATE_LIMIT_INGEST)
async def ingest_url_endpoint(request: Request, req: IngestURLRequest):
    """Ingest content from a YouTube video URL or website link."""
    source_type = detect_source_type(req.url)
    if source_type not in ("youtube", "website"):
        raise HTTPException(
            status_code=400,
            detail="URL must be a YouTube video link or a website URL (http/https).",
        )

    try:
        chunks_created, source_label = ingest_url(req.url, topic=req.topic)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception("Ingestion failed")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}")

    return IngestURLResponse(
        message=f"Successfully ingested {source_type} content.",
        source=source_label,
        source_type=source_type,
        chunks_created=chunks_created,
    )
