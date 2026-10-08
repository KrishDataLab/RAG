import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.db.repositories import DatabaseRepository, SessionLocal
from app.retrieval.vector_store import VectorStore

def main():
    db = SessionLocal()
    repo = DatabaseRepository(db)
    vs = VectorStore()

    # Get all entities in DB
    entities = repo.get_entities()
    print(f"Total entities in DB: {len(entities)}")

    queries = [
        ("Q-03", "What signal is carried by port PPort_EngineSpeed?", [2]),
        ("Q-06", "What interface does SWC_TorqueCalc provide to SWC_ThrottleActuator?", [2]),
        ("Q-07", "What range and resolution is specified for signal EngineSpeed_RPM?", [2]),
        ("Q-09", "What port type is PPort_ThrottleCmd?", [2]),
        ("Q-16", "What RPort is owned by SWC_ThrottleActuator?", [2]),
        ("Q-17", "Which safety standard is referenced by SWC_SafetyMonitor?", [1]),
        ("Q-19", "What is the signal carried by RPort_SafetyCheck?", [2])
    ]

    for q_id, q_text, exp_pages in queries:
        # Vector search
        vec_res = vs.search(query=q_text, top_k=8)

        # Entity match search
        matched_chunk_ids = set()
        q_words = q_text.replace("?", "").replace(",", "").split()
        for e in entities:
            name = e.canonical_name
            if any(w.lower() == name.lower() or (len(name) > 3 and name.lower() in q_text.lower()) for w in q_words):
                # find sources for this entity
                sources = repo.get_sources_for_entity(e.id) if hasattr(repo, 'get_sources_for_entity') else []
                for s in sources:
                    if hasattr(s, 'chunk_id') and s.chunk_id:
                        matched_chunk_ids.add(s.chunk_id)

        print(f"\n[{q_id}] Query: {q_text}")
        print(f"  Expected Pages: {exp_pages}")
        print(f"  Vector Search Top 4 Pages: {[r['metadata'].get('page_number') for r in vec_res[:4]]}")
        print(f"  Matched Entity Chunk IDs: {matched_chunk_ids}")

if __name__ == "__main__":
    main()
