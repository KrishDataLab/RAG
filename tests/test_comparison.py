from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.models import Base
from app.db.repositories import DatabaseRepository
from app.comparison.rules import InconsistencyRulesEngine

def test_inconsistency_rules():
    entities_a = [{"name": "SWC_SpeedSensor", "entity_type": "SoftwareComponent"}]
    rels_a = [{"source_name": "SWC_SpeedSensor", "target_name": "RTE_I_EngineSpeed", "relationship_type": "provides"}]

    entities_b = [{"name": "SWC_SpeedSensor_V2", "entity_type": "SoftwareComponent"}]
    rels_b = [
        {"source_name": "SWC_SpeedSensor_V2", "target_name": "RTE_I_EngineSpeed_HighRes", "relationship_type": "provides"},
        {"source_name": "SWC_TorqueCalc", "target_name": "RTE_I_EngineSpeed", "relationship_type": "requires"}
    ]

    findings = InconsistencyRulesEngine.run_rules(
        entities_a, rels_a, entities_b, rels_b, "DOC-A", "DOC-B"
    )
    assert len(findings) > 0
    assert findings[0]["type"] == "INTERFACE_MISMATCH"

def test_relationships_persist_when_entities_were_saved_separately():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    repo = DatabaseRepository(session)
    repo.get_or_create_project("P_REL")
    repo.create_document("DOC-REL", "P_REL", "relationship.pdf", "v1.0", "hash", 1)
    repo.save_entities_and_relationships(
        "DOC-REL",
        [
            {"type": "SoftwareComponent", "name": "SWC_Provider"},
            {"type": "Interface", "name": "RTE_I_Test"},
        ],
        [],
    )

    repo.save_entities_and_relationships(
        "DOC-REL",
        [],
        [{
            "source_name": "SWC_Provider",
            "target_name": "RTE_I_Test",
            "relationship_type": "provides",
            "source_page": 1,
        }],
    )

    relationships = repo.get_relationships("DOC-REL")
    session.close()
    engine.dispose()

    assert len(relationships) == 1
    assert relationships[0]["relationship_type"] == "provides"
