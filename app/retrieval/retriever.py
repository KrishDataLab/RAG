from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.retrieval.vector_store import MemoryVectorStore


class ArchitectureRetriever:
    def __init__(self, vector_store: MemoryVectorStore):
        self.vector_store = vector_store
        self.default_top_k = settings.retrieval_config.get("retrieval", {}).get("top_k", 8)

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        project_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        return self.vector_store.search(
            query=query,
            top_k=self.default_top_k if top_k is None else top_k,
            project_id=project_id,
            document_ids=document_ids,
        )
