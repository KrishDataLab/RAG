from fastapi import APIRouter, Depends
from app.api.deps import get_repo, get_retriever, get_llm_client
from app.db.repositories import DatabaseRepository
from app.retrieval.retriever import ArchitectureRetriever
from app.llm.client import LLMClient
from app.evaluation.runners import EvaluationRunner
from app.evaluation.reports import EvaluationReportExporter

router = APIRouter()

@router.post("/evaluation/run")
def run_evaluation(
    project_id: str = "P001",
    document_id: str = None,
    repo: DatabaseRepository = Depends(get_repo),
    retriever: ArchitectureRetriever = Depends(get_retriever),
    llm_client: LLMClient = Depends(get_llm_client)
):
    runner = EvaluationRunner(retriever, llm_client, repo)
    results = runner.run_benchmark(project_id=project_id, doc_id=document_id)
    
    json_file, csv_file = EvaluationReportExporter.export_results(results)
    results["artifacts"] = {
        "json": json_file,
        "csv": csv_file
    }
    return results

@router.get("/audit_logs")
def list_audit_logs(project_id: str = "P001", repo: DatabaseRepository = Depends(get_repo)):
    logs = repo.get_audit_logs(project_id)
    return [
        {
            "id": l.id,
            "user_id": l.user_id,
            "action": l.action,
            "resource_type": l.resource_type,
            "resource_id": l.resource_id,
            "created_at": l.created_at.isoformat() if l.created_at else ""
        } for l in logs
    ]
