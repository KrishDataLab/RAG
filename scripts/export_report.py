import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.db.repositories import DatabaseRepository, SessionLocal

def main():
    db = SessionLocal()
    repo = DatabaseRepository(db)
    docs = repo.get_documents("P001")
    entities = repo.get_entities()
    findings = repo.get_findings("P001")

    report = {
        "project_id": "P001",
        "documents": [{"id": d.id, "name": d.name, "version": d.version_label} for d in docs],
        "entities_count": len(entities),
        "findings_count": len(findings),
        "findings": findings
    }

    out_path = BASE_DIR / "data" / "processed" / "architecture_summary_report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Summary report exported to {out_path}")

if __name__ == "__main__":
    main()
