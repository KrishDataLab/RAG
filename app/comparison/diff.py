from typing import List, Dict, Any
from app.comparison.aligner import RevisionAligner
from app.comparison.rules import InconsistencyRulesEngine
from app.db.repositories import DatabaseRepository
from app.llm.client import LLMClient
from app.llm.prompts import prompt_manager

class RevisionComparator:
    def __init__(self, repo: DatabaseRepository, llm_client: LLMClient):
        self.repo = repo
        self.llm_client = llm_client

    def compare_documents(self, doc_a_id: str, doc_b_id: str, project_id: str = "P001") -> Dict[str, Any]:
        doc_a = self.repo.get_document_by_id(doc_a_id)
        doc_b = self.repo.get_document_by_id(doc_b_id)

        entities_a = [e.__dict__ for e in self.repo.get_entities(doc_a_id)]
        entities_b = [e.__dict__ for e in self.repo.get_entities(doc_b_id)]

        # Fallback to general project entities if document-specific entities are stored under a previous ingestion run
        if not entities_a:
            all_ents = [e.__dict__ for e in self.repo.get_entities()]
            entities_a = [e for e in all_ents if e.get("extraction_version") == "v1.0" or "v1.0" in e.get("document_id", "")]
        if not entities_b:
            all_ents = [e.__dict__ for e in self.repo.get_entities()]
            entities_b = [e for e in all_ents if e.get("extraction_version") == "v1.1" or "v1.1" in e.get("document_id", "")]

        # Clean dict objects from SQLAlchemy
        for e in entities_a + entities_b:
            e.pop("_sa_instance_state", None)
            e["name"] = e.get("canonical_name", e.get("name", ""))
            e["type"] = e.get("entity_type", e.get("type", "SoftwareComponent"))

        rels_a = self.repo.get_relationships(doc_a_id) or self.repo.get_relationships()
        rels_b = self.repo.get_relationships(doc_b_id) or self.repo.get_relationships()

        # 1. Align Entities
        aligned = RevisionAligner.align_entities(entities_a, entities_b)

        # 2. Run Deterministic Inconsistency Rules
        rule_findings = InconsistencyRulesEngine.run_rules(
            entities_a, rels_a, entities_b, rels_b, doc_a_id, doc_b_id
        )

        # 3. Store Findings in Database
        saved_findings = []
        for rf in rule_findings:
            explanation_prompt = prompt_manager.render(
                "inconsistency_explanation_v1.txt",
                rule_name=rf["type"],
                finding_summary=rf["summary"],
                evidence_a=f"Doc A ({doc_a.name if doc_a else doc_a_id})",
                evidence_b=f"Doc B ({doc_b.name if doc_b else doc_b_id})"
            )
            ai_desc = self.llm_client.generate(explanation_prompt)
            
            finding_rec = self.repo.create_finding(
                project_id=project_id,
                ftype=rf["type"],
                severity=rf["severity"],
                summary=rf["summary"],
                description=rf["description"] + "\n\nAI Explanation:\n" + ai_desc,
                evidence_list=rf["evidences"]
            )
            saved_findings.append({
                "id": finding_rec.id,
                "type": finding_rec.type,
                "severity": finding_rec.severity,
                "summary": finding_rec.summary,
                "description": finding_rec.description
            })

        return {
            "document_a": {"id": doc_a_id, "name": doc_a.name if doc_a else ""},
            "document_b": {"id": doc_b_id, "name": doc_b.name if doc_b else ""},
            "alignment": aligned,
            "findings_count": len(saved_findings),
            "findings": saved_findings
        }
