import uuid
import json
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models import (
    Project, User, Document, DocumentChunk, Entity, EntitySource,
    EntityRelationship, Finding, FindingEvidence, FindingReview, AuditLog, init_db, SessionLocal
)
from app.core.logging import logger

init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class DatabaseRepository:
    def __init__(self, db: Session):
        self.db = db

    def log_audit(self, action: str, resource_type: str, resource_id: str, user_id: str = "system", project_id: str = "P001", metadata: dict = None):
        audit = AuditLog(
            id=f"AUD-{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            project_id=project_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata_json=json.dumps(metadata or {}),
            created_at=datetime.utcnow()
        )
        self.db.add(audit)
        self.db.commit()

    def get_or_create_project(self, project_id: str = "P001", name: str = "Powertrain ECU AUTOSAR Architecture") -> Project:
        proj = self.db.query(Project).filter(Project.id == project_id).first()
        if not proj:
            proj = Project(id=project_id, name=name, status="ACTIVE")
            self.db.add(proj)
            self.db.commit()
            self.db.refresh(proj)
            self.log_audit("CREATE_PROJECT", "Project", project_id)
        return proj

    def create_document(self, doc_id: str, project_id: str, name: str, version_label: str, sha256: str, page_count: int) -> Document:
        doc = Document(
            id=doc_id,
            project_id=project_id,
            name=name,
            version_label=version_label,
            sha256=sha256,
            page_count=page_count,
            ingestion_status="PROCESSING"
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        self.log_audit("UPLOAD_DOCUMENT", "Document", doc_id, project_id=project_id)
        return doc

    def update_document_status(self, doc_id: str, status: str):
        doc = self.db.query(Document).filter(Document.id == doc_id).first()
        if doc:
            doc.ingestion_status = status
            self.db.commit()
            self.log_audit("UPDATE_DOCUMENT_STATUS", "Document", doc_id, metadata={"status": status})

    def get_documents(self, project_id: Optional[str] = None) -> List[Document]:
        query = self.db.query(Document)
        if project_id:
            query = query.filter(Document.project_id == project_id)
        return query.all()

    def get_document_by_id(self, doc_id: str) -> Optional[Document]:
        return self.db.query(Document).filter(Document.id == doc_id).first()

    def save_chunks(self, chunks_data: List[dict]):
        for data in chunks_data:
            chunk = DocumentChunk(
                id=f"DC-{uuid.uuid4().hex[:8]}",
                document_id=data["document_id"],
                chunk_id=data["chunk_id"],
                page_number=data["page_number"],
                section=data.get("section", "General"),
                subsection=data.get("subsection", ""),
                text=data["text"]
            )
            self.db.add(chunk)
        self.db.commit()

    def get_chunks_by_document(self, doc_id: str) -> List[DocumentChunk]:
        return self.db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).all()

    def save_entities_and_relationships(self, doc_id: str, entities_data: List[dict], rels_data: List[dict]):
        entity_map = {}
        for edata in entities_data:
            entity_id = f"ENT-{uuid.uuid4().hex[:8]}"
            ent = Entity(
                id=entity_id,
                document_id=doc_id,
                entity_type=edata["type"],
                canonical_name=edata["name"],
                aliases_json=json.dumps(edata.get("aliases", [])),
                confidence=edata.get("confidence", 1.0)
            )
            self.db.add(ent)
            entity_map[edata["name"]] = entity_id

            # source link
            source = EntitySource(
                id=f"ES-{uuid.uuid4().hex[:8]}",
                entity_id=entity_id,
                document_id=doc_id,
                page_number=edata.get("page_number", 1),
                section=edata.get("section", ""),
                text_span=edata.get("name", "")
            )
            self.db.add(source)

        self.db.commit()

        # save relationships
        for entity in self.get_entities(doc_id):
            entity_map.setdefault(entity.canonical_name, entity.id)

        for rdata in rels_data:
            src_name = rdata.get("source_name")
            tgt_name = rdata.get("target_name")
            
            src_id = entity_map.get(src_name)
            tgt_id = entity_map.get(tgt_name)
            
            if src_id and tgt_id:
                rel = EntityRelationship(
                    id=f"REL-{uuid.uuid4().hex[:8]}",
                    source_entity_id=src_id,
                    target_entity_id=tgt_id,
                    relationship_type=rdata.get("relationship_type", "uses"),
                    confidence=rdata.get("confidence", 1.0),
                    source_document_id=doc_id,
                    source_page=rdata.get("source_page", 1)
                )
                self.db.add(rel)

        self.db.commit()
        self.log_audit("EXTRACT_KNOWLEDGE", "Document", doc_id, metadata={"entities_count": len(entities_data), "relationships_count": len(rels_data)})

    def get_entities(self, doc_id: Optional[str] = None) -> List[Entity]:
        query = self.db.query(Entity)
        if doc_id:
            query = query.filter(Entity.document_id == doc_id)
        return query.all()

    def get_relationships(self, doc_id: Optional[str] = None) -> List[dict]:
        query = self.db.query(EntityRelationship)
        if doc_id:
            query = query.filter(EntityRelationship.source_document_id == doc_id)
        rels = query.all()
        
        results = []
        for r in rels:
            src_ent = self.db.query(Entity).filter(Entity.id == r.source_entity_id).first()
            tgt_ent = self.db.query(Entity).filter(Entity.id == r.target_entity_id).first()
            if src_ent and tgt_ent:
                results.append({
                    "id": r.id,
                    "source_name": src_ent.canonical_name,
                    "source_type": src_ent.entity_type,
                    "target_name": tgt_ent.canonical_name,
                    "target_type": tgt_ent.entity_type,
                    "relationship_type": r.relationship_type,
                    "confidence": r.confidence,
                    "document_id": r.source_document_id,
                    "source_page": r.source_page
                })
        return results

    def create_finding(self, project_id: str, ftype: str, severity: str, summary: str, description: str, evidence_list: List[dict]) -> Finding:
        fid = f"FIND-{uuid.uuid4().hex[:8]}"
        finding = Finding(
            id=fid,
            project_id=project_id,
            type=ftype,
            severity=severity,
            summary=summary,
            description=description,
            status="NEEDS_REVIEW"
        )
        self.db.add(finding)
        self.db.commit()

        for ev in evidence_list:
            fev = FindingEvidence(
                id=f"EVI-{uuid.uuid4().hex[:8]}",
                finding_id=fid,
                document_id=ev.get("document_id", ""),
                page_number=ev.get("page_number", 1),
                chunk_id=ev.get("chunk_id", ""),
                claim_text=ev.get("claim_text", "")
            )
            self.db.add(fev)
        
        self.db.commit()
        self.log_audit("CREATE_FINDING", "Finding", fid, project_id=project_id)
        return finding

    def get_findings(self, project_id: Optional[str] = None, status: Optional[str] = None) -> List[dict]:
        query = self.db.query(Finding)
        if project_id:
            query = query.filter(Finding.project_id == project_id)
        if status:
            query = query.filter(Finding.status == status)
        findings = query.all()

        results = []
        for f in findings:
            evidences = self.db.query(FindingEvidence).filter(FindingEvidence.finding_id == f.id).all()
            reviews = self.db.query(FindingReview).filter(FindingReview.finding_id == f.id).all()
            results.append({
                "id": f.id,
                "project_id": f.project_id,
                "type": f.type,
                "severity": f.severity,
                "summary": f.summary,
                "description": f.description,
                "status": f.status,
                "created_at": f.created_at.isoformat() if f.created_at else "",
                "evidences": [{"document_id": e.document_id, "page_number": e.page_number, "claim_text": e.claim_text} for e in evidences],
                "reviews": [{"reviewer_id": r.reviewer_id, "old_status": r.old_status, "new_status": r.new_status, "comment": r.comment, "created_at": r.created_at.isoformat()} for r in reviews]
            })
        return results

    def review_finding(self, finding_id: str, reviewer_id: str, new_status: str, comment: str) -> Optional[Finding]:
        finding = self.db.query(Finding).filter(Finding.id == finding_id).first()
        if not finding:
            return None
        
        old_status = finding.status
        finding.status = new_status
        finding.updated_at = datetime.utcnow()

        review = FindingReview(
            id=f"REV-{uuid.uuid4().hex[:8]}",
            finding_id=finding_id,
            reviewer_id=reviewer_id,
            old_status=old_status,
            new_status=new_status,
            comment=comment
        )
        self.db.add(review)
        self.db.commit()

        self.log_audit(
            "REVIEW_FINDING", "Finding", finding_id,
            user_id=reviewer_id,
            metadata={"old_status": old_status, "new_status": new_status, "comment": comment}
        )
        return finding

    def get_audit_logs(self, project_id: Optional[str] = None) -> List[AuditLog]:
        query = self.db.query(AuditLog)
        if project_id:
            query = query.filter(AuditLog.project_id == project_id)
        return query.order_by(AuditLog.created_at.desc()).all()
