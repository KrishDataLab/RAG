from fastapi import APIRouter, Depends
from typing import Optional
from app.api.deps import get_repo, get_llm_client
from app.db.repositories import DatabaseRepository
from app.llm.client import LLMClient
from app.extraction.entities import EntityExtractor
from app.extraction.relationships import RelationshipExtractor

router = APIRouter()

@router.post("/documents/{document_id}/extract/entities")
def extract_entities(document_id: str, repo: DatabaseRepository = Depends(get_repo), llm_client: LLMClient = Depends(get_llm_client)):
    chunks_rec = repo.get_chunks_by_document(document_id)
    chunks_data = [c.__dict__ for c in chunks_rec]
    for c in chunks_data:
        c.pop("_sa_instance_state", None)

    extractor = EntityExtractor(llm_client)
    entities = extractor.extract_from_chunks(chunks_data)
    
    # Save entities to DB
    repo.save_entities_and_relationships(document_id, entities, [])

    return {
        "status": "SUCCESS",
        "document_id": document_id,
        "entities_count": len(entities),
        "entities": entities
    }

@router.post("/documents/{document_id}/extract/relationships")
def extract_relationships(document_id: str, repo: DatabaseRepository = Depends(get_repo), llm_client: LLMClient = Depends(get_llm_client)):
    chunks_rec = repo.get_chunks_by_document(document_id)
    chunks_data = [c.__dict__ for c in chunks_rec]
    for c in chunks_data:
        c.pop("_sa_instance_state", None)

    db_entities = [
        {"name": e.canonical_name, "type": e.entity_type, "page_number": 1, "section": ""}
        for e in repo.get_entities(document_id)
    ]

    rel_extractor = RelationshipExtractor(llm_client)
    rels = rel_extractor.extract_relationships(chunks_data, db_entities)

    repo.save_entities_and_relationships(document_id, [], rels)

    return {
        "status": "SUCCESS",
        "document_id": document_id,
        "relationships_count": len(rels),
        "relationships": rels
    }

@router.get("/documents/{document_id}/architecture")
def get_architecture_inventory(document_id: Optional[str] = None, repo: DatabaseRepository = Depends(get_repo)):
    entities = repo.get_entities(document_id)
    relationships = repo.get_relationships(document_id)

    return {
        "entities": [
            {
                "id": e.id,
                "name": e.canonical_name,
                "type": e.entity_type,
                "document_id": e.document_id,
                "confidence": e.confidence
            } for e in entities
        ],
        "relationships": relationships
    }
