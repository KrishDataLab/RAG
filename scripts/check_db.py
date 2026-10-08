import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.db.repositories import DatabaseRepository, SessionLocal

def main():
    db = SessionLocal()
    repo = DatabaseRepository(db)
    docs = repo.get_documents()
    print("Documents in DB:")
    for d in docs:
        print(d.id, d.name, d.version_label)
        ents = repo.get_entities(d.id)
        rels = repo.get_relationships(d.id)
        print(f"  Entities ({len(ents)}): {[e.canonical_name for e in ents]}")
        print("  Relationships:")
        for r in rels:
            print(f"    {r.get('source_name')} --[{r.get('relationship_type')}]--> {r.get('target_name')}")

if __name__ == "__main__":
    main()
