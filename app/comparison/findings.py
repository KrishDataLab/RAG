from typing import List, Dict, Any, Optional
from app.db.repositories import DatabaseRepository

class FindingsManager:
    def __init__(self, repo: DatabaseRepository):
        self.repo = repo

    def list_findings(self, project_id: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.repo.get_findings(project_id=project_id, status=status)

    def review(self, finding_id: str, reviewer_id: str, new_status: str, comment: str) -> Optional[Dict[str, Any]]:
        updated = self.repo.review_finding(
            finding_id=finding_id,
            reviewer_id=reviewer_id,
            new_status=new_status,
            comment=comment
        )
        if updated:
            return {
                "id": updated.id,
                "status": updated.status,
                "updated_at": updated.updated_at.isoformat()
            }
        return None
