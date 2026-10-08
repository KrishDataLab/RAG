from fastapi import APIRouter, Depends
from app.api.schemas.requests import CompareRequest
from app.api.deps import get_repo, get_llm_client
from app.db.repositories import DatabaseRepository
from app.llm.client import LLMClient
from app.comparison.diff import RevisionComparator

router = APIRouter()

@router.post("/compare")
def compare_revisions(req: CompareRequest, repo: DatabaseRepository = Depends(get_repo), llm_client: LLMClient = Depends(get_llm_client)):
    comparator = RevisionComparator(repo, llm_client)
    res = comparator.compare_documents(req.document_a_id, req.document_b_id, project_id=req.project_id)
    return res
