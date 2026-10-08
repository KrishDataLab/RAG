import uuid
from typing import Dict, Any

class MetadataExtractor:
    @staticmethod
    def create_document_metadata(project_id: str, file_name: str, version_label: str, sha256: str, page_count: int) -> Dict[str, Any]:
        doc_id = f"DOC-{uuid.uuid4().hex[:8].upper()}"
        return {
            "document_id": doc_id,
            "project_id": project_id,
            "document_name": file_name,
            "version_label": version_label,
            "sha256": sha256,
            "page_count": page_count,
            "source_type": "HLD"
        }
