from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()

@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "retrieval": "bm25",
        "llm_mode": "external provider when configured; otherwise local fallback",
        "app_name": settings.APP_NAME
    }
