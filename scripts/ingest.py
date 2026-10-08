import sys
import argparse
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.db.repositories import DatabaseRepository, SessionLocal
from app.retrieval.vector_store import VectorStore
from app.ingestion.pipeline import IngestionPipeline

def main():
    parser = argparse.ArgumentParser(description="AHITA Document Ingestion CLI")
    parser.add_argument("--pdf", required=True, help="Path to HLD PDF document")
    parser.add_argument("--project-id", default="P001", help="Project ID (default: P001)")
    parser.add_argument("--version-label", default="v1.0", help="Document version label (default: v1.0)")
    args = parser.parse_args()

    db = SessionLocal()
    repo = DatabaseRepository(db)
    vector_store = VectorStore()

    pipeline = IngestionPipeline(repo, vector_store)
    result = pipeline.run(file_path=args.pdf, project_id=args.project_id, version_label=args.version_label)

    print("Ingestion Result:")
    print(result)

if __name__ == "__main__":
    main()
