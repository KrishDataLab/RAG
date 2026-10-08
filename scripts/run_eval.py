import os
import sys
import json
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.db.repositories import DatabaseRepository, SessionLocal
from app.retrieval.vector_store import MemoryVectorStore
from app.retrieval.retriever import ArchitectureRetriever
from app.llm.client import LLMClient
from app.ingestion.pipeline import IngestionPipeline
from app.extraction.entities import EntityExtractor
from app.extraction.relationships import RelationshipExtractor
from app.comparison.diff import RevisionComparator
from app.evaluation.runners import EvaluationRunner
from app.evaluation.reports import EvaluationReportExporter

def main():
    print("==================================================")
    print("   AHITA Capstone Evaluation & Benchmark Suite   ")
    print("==================================================")

    db = SessionLocal()
    repo = DatabaseRepository(db)
    vector_store = MemoryVectorStore(load_existing=True)
    llm_client = LLMClient()
    retriever = ArchitectureRetriever(vector_store)

    # 1. Ingest sample PDFs
    sample_v1 = BASE_DIR.parent / "Input_Data" / "T03_HLD_v1.0_EngineControl_v1.0.pdf"
    sample_v2 = BASE_DIR.parent / "Input_Data" / "T03_HLD_v1.1_EngineControl_v1.0.pdf"

    if sample_v1.exists() and sample_v2.exists():
        print("\n[Step 1] Ingesting sample AUTOSAR HLD documents...")
        pipeline = IngestionPipeline(repo, vector_store)
        res_v1 = pipeline.run(file_path=str(sample_v1), project_id="P001", version_label="v1.0")
        res_v2 = pipeline.run(file_path=str(sample_v2), project_id="P001", version_label="v1.1")
        
        doc_v1_id = res_v1["document_id"]
        doc_v2_id = res_v2["document_id"]

        print("\n[Step 2] Extracting architectural entities & relationships for Version A & Version B...")
        extractor = EntityExtractor(llm_client)
        rel_extractor = RelationshipExtractor(llm_client)

        # Extract for Version A
        chunks_rec_a = repo.get_chunks_by_document(doc_v1_id)
        chunks_data_a = [c.__dict__ for c in chunks_rec_a]
        for c in chunks_data_a: c.pop("_sa_instance_state", None)
        entities_a = extractor.extract_from_chunks(chunks_data_a)
        rels_a = rel_extractor.extract_relationships(chunks_data_a, entities_a)
        repo.save_entities_and_relationships(doc_v1_id, entities_a, rels_a)

        # Extract for Version B
        chunks_rec_b = repo.get_chunks_by_document(doc_v2_id)
        chunks_data_b = [c.__dict__ for c in chunks_rec_b]
        for c in chunks_data_b: c.pop("_sa_instance_state", None)
        entities_b = extractor.extract_from_chunks(chunks_data_b)
        rels_b = rel_extractor.extract_relationships(chunks_data_b, entities_b)
        repo.save_entities_and_relationships(doc_v2_id, entities_b, rels_b)

        print("\n[Step 3] Running revision comparison & inconsistency detection...")
        comparator = RevisionComparator(repo, llm_client)
        comp_res = comparator.compare_documents(doc_v1_id, doc_v2_id, project_id="P001")
        print(f"Detected {comp_res['findings_count']} inconsistency findings.")

    print("\n[Step 4] Running RAG Benchmark Evaluation...")
    runner = EvaluationRunner(retriever, llm_client, repo)
    results = runner.run_benchmark(version="v2", project_id="P001")

    # Export to Evaluation_Results/ as well as root EVALUATION_RESULTS.json / .csv
    json_path, csv_path = EvaluationReportExporter.export_results(results)

    root_json = BASE_DIR / "EVALUATION_RESULTS.json"
    root_csv = BASE_DIR / "EVALUATION_RESULTS.csv"

    with open(root_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    pd.DataFrame(results.get("question_details", [])).to_csv(root_csv, index=False)

    print("\n==================================================")
    print("              EVALUATION SUMMARY RESULTS          ")
    print("==================================================")
    for k, v in results["summary"].items():
        print(f"  {k:30s}: {v}")
    print("==================================================")
    print(f"\nArtifacts generated successfully:\n- {root_json}\n- {root_csv}\n- {json_path}\n- {csv_path}")

if __name__ == "__main__":
    main()
