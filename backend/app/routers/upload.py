from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from app.core.config import UPLOAD_DIR
from app.core.rate_limit import RATE_LIMIT_UPLOAD, limiter
from app.models.schemas import UploadResponse
from app.services.ingestion import ALL_FILE_EXTENSIONS, detect_source_type, ingest_file

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB (larger to support video/audio)

router = APIRouter(prefix="/api/upload", tags=["Upload"])


def _validate_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal."""
    from pathlib import PurePosixPath

    safe = PurePosixPath(filename).name
    if not safe:
        raise HTTPException(status_code=400, detail="Invalid filename.")
    return safe


@router.post("/", response_model=UploadResponse)
@limiter.limit(RATE_LIMIT_UPLOAD)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    topic: str = Form(default="General"),
):
    filename = _validate_filename(file.filename or "upload.txt")
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALL_FILE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(ALL_FILE_EXTENSIONS)}",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 50 MB limit.")

    save_path = UPLOAD_DIR / filename
    save_path.write_bytes(file_bytes)

    try:
        source_type = detect_source_type(filename)
        chunks_created = ingest_file(file_bytes, filename, topic=topic)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return UploadResponse(
        message="File processed successfully.",
        filename=filename,
        chunks_created=chunks_created,
        source_type=source_type,
    )
