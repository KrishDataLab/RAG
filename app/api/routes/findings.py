from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from app.api.schemas.requests import ReviewFindingRequest
from app.api.deps import get_repo
from app.db.repositories import DatabaseRepository
from app.comparison.findings import FindingsManager

router = APIRouter()

@router.get("/findings")
def list_findings(project_id: Optional[str] = "P001", status: Optional[str] = None, repo: DatabaseRepository = Depends(get_repo)):
    manager = FindingsManager(repo)
    return manager.list_findings(project_id=project_id, status=status)

@router.post("/findings/{finding_id}/review")
def review_finding(finding_id: str, req: ReviewFindingRequest, repo: DatabaseRepository = Depends(get_repo)):
    manager = FindingsManager(repo)
    result = manager.review(
        finding_id=finding_id,
        reviewer_id=req.reviewer_id,
        new_status=req.status,
        comment=req.comment
    )
    if not result:
        raise HTTPException(status_code=404, detail="Finding not found.")
    return result
