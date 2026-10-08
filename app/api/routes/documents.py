import os
import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from typing import Optional, List
from app.api.deps import get_repo, get_vector_store
from app.db.repositories import DatabaseRepository
from app.retrieval.vector_store import MemoryVectorStore
from app.ingestion.pipeline import IngestionPipeline
from app.core.config import settings
from app.core.exceptions import DocumentProcessingError

router = APIRouter()

@router.post("/documents")
def upload_document(
    file: UploadFile = File(...),
    project_id: str = Form("P001"),
    version_label: str = Form("v1.0"),
    repo: DatabaseRepository = Depends(get_repo)
):
    # Sanitize filename against path traversal attacks
    safe_filename = os.path.basename((file.filename or "").replace("\\", "/"))
    if not safe_filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    abs_upload_dir = Path(settings.UPLOAD_DIR).resolve()
    stored_filename = f"{uuid.uuid4().hex}_{safe_filename}"
    save_path = (abs_upload_dir / stored_filename).resolve()

    if save_path.parent != abs_upload_dir:
        raise HTTPException(status_code=400, detail="Invalid filename or path traversal detected.")

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    repo.get_or_create_project(project_id)

    return {
        "status": "UPLOADED",
        "file_name": safe_filename,
        "file_path": str(save_path),
        "project_id": project_id,
        "version_label": version_label
    }

@router.get("/documents")
def list_documents(project_id: Optional[str] = "P001", repo: DatabaseRepository = Depends(get_repo)):
    docs = repo.get_documents(project_id)
    return [
        {
            "id": d.id,
            "name": d.name,
            "version_label": d.version_label,
            "page_count": d.page_count,
            "ingestion_status": d.ingestion_status,
            "created_at": d.created_at.isoformat() if d.created_at else ""
        } for d in docs
    ]

@router.post("/documents/{document_id}/ingest")
def ingest_document(
    document_id: str = None,
    file_path: str = Form(...),
    project_id: str = Form("P001"),
    version_label: str = Form("v1.0"),
    repo: DatabaseRepository = Depends(get_repo),
    vector_store: MemoryVectorStore = Depends(get_vector_store)
):
    abs_path = Path(file_path).resolve()
    allowed_dirs = [Path(settings.UPLOAD_DIR).resolve(), (settings.BASE_DIR / "data").resolve()]
    if not any(abs_path.is_relative_to(allowed_dir) for allowed_dir in allowed_dirs):
        raise HTTPException(status_code=400, detail="Invalid file_path: File must be within approved data or upload directory.")

    pipeline = IngestionPipeline(repo, vector_store)
    try:
        result = pipeline.run(file_path=str(abs_path), project_id=project_id, version_label=version_label)
    except DocumentProcessingError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return result
