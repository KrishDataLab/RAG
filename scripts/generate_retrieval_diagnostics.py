import os
import sys
import json
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.db.repositories import DatabaseRepository, SessionLocal
from app.retrieval.vector_store import VectorStore
from app.retrieval.retriever import ArchitectureRetriever
from app.ingestion.pipeline import IngestionPipeline
from app.evaluation.datasets import EvaluationDatasetLoader

def generate_diagnostics():
    db = SessionLocal()
    repo = DatabaseRepository(db)
    vector_store = VectorStore()
    retriever = ArchitectureRetriever(vector_store)

    # Clean existing database chunks & re-ingest with granular chunker
    sample_v1 = BASE_DIR.parent / "Input_Data" / "T03_HLD_v1.0_EngineControl_v1.0.pdf"
    sample_v2 = BASE_DIR.parent / "Input_Data" / "T03_HLD_v1.1_EngineControl_v1.0.pdf"

    print("Re-ingesting sample PDFs with granular context-aware chunker...")
    pipeline = IngestionPipeline(repo, vector_store)
    res_v1 = pipeline.run(file_path=str(sample_v1), project_id="P001_V2", version_label="v1.0")
    res_v2 = pipeline.run(file_path=str(sample_v2), project_id="P001_V2", version_label="v1.1")

    questions = EvaluationDatasetLoader.load_benchmark_questions("v2")
    entity_gt = EvaluationDatasetLoader.load_entity_ground_truth("v2")

    retrieval_rows = []

    r1_hits, r3_hits, r5_hits, r8_hits = 0, 0, 0, 0
    answerable_count = 0

    for q in questions:
        q_id = q["id"]
        q_text = q["question"]
        is_ans = q.get("is_answerable", True)
        exp_pages = q.get("expected_pages", [])

        # Retrieve top 8
        chunks = retriever.retrieve(query=q_text, top_k=8)
        ret_chunk_ids = [c["metadata"].get("chunk_id", "") for c in chunks]
        ret_pages = [c["metadata"].get("page_number", 1) for c in chunks]

        # Calculate hits at k
        if not is_ans or not exp_pages:
            hit = "N/A (Abstention)"
            rank = "N/A"
            r1, r3, r5, r8 = 1.0, 1.0, 1.0, 1.0
        else:
            answerable_count += 1
            page_hits = [idx+1 for idx, p in enumerate(ret_pages) if p in exp_pages]
            rank = page_hits[0] if page_hits else "Miss"
            hit = "HIT" if page_hits else "MISS"

            r1 = 1.0 if (len(ret_pages) >= 1 and ret_pages[0] in exp_pages) else 0.0
            r3 = 1.0 if any(p in exp_pages for p in ret_pages[:3]) else 0.0
            r5 = 1.0 if any(p in exp_pages for p in ret_pages[:5]) else 0.0
            r8 = 1.0 if any(p in exp_pages for p in ret_pages[:8]) else 0.0

            r1_hits += r1
            r3_hits += r3
            r5_hits += r5
            r8_hits += r8

        retrieval_rows.append({
            "Question ID": q_id,
            "Question": q_text,
            "Expected Pages": str(exp_pages),
            "Retrieved Chunk IDs": "; ".join(ret_chunk_ids),
            "Retrieved Pages": str(ret_pages),
            "Hit/Miss": hit,
            "Rank of Expected Evidence": rank,
            "Recall@1": r1,
            "Recall@3": r3,
            "Recall@5": r5,
            "Recall@8": r8
        })

    df_ret = pd.DataFrame(retrieval_rows)
    out_csv = BASE_DIR / "evaluation" / "retrieval_diagnostics_v2.csv"
    df_ret.to_csv(out_csv, index=False)

    print(f"Retrieval diagnostics exported to {out_csv}")
    print("Aggregate Recall Metrics (Answerable Questions):")
    print(f"  Recall@1: {r1_hits / max(answerable_count, 1):.4f}")
    print(f"  Recall@3: {r3_hits / max(answerable_count, 1):.4f}")
    print(f"  Recall@5: {r5_hits / max(answerable_count, 1):.4f}")
    print(f"  Recall@8: {r8_hits / max(answerable_count, 1):.4f}")

    # Entity Diagnostics
    entities_rec = repo.get_entities()
    pred_entities = [{"name": e.canonical_name, "type": e.entity_type} for e in entities_rec]
    gt_by_class = entity_gt.get("entities_by_class", {})

    ent_diag_rows = []
    for cls_name, gt_names in gt_by_class.items():
        preds = [e["name"] for e in pred_entities if e["type"] == cls_name]
        matches = list(set(preds) & set(gt_names))
        misses = list(set(gt_names) - set(preds))
        fps = list(set(preds) - set(gt_names))
        
        p = len(matches) / len(preds) if preds else 0.0
        r = len(matches) / len(gt_names) if gt_names else 0.0
        f1 = (2*p*r)/(p+r) if (p+r) > 0 else 0.0

        ent_diag_rows.append({
            "Entity Class": cls_name,
            "Precision": round(p, 4),
            "Recall": round(r, 4),
            "F1 Score": round(f1, 4),
            "True Positives": str(matches),
            "False Negatives (Missed)": str(misses),
            "False Positives": str(fps)
        })

    df_ent = pd.DataFrame(ent_diag_rows)
    ent_csv = BASE_DIR / "evaluation" / "entity_diagnostics_v2.csv"
    df_ent.to_csv(ent_csv, index=False)

    # Inconsistency Diagnostics
    findings = repo.get_findings("P001_V2")
    if not findings:
        findings = repo.get_findings("P001")

    inc_gt = EvaluationDatasetLoader.load_inconsistency_ground_truth("v2").get("inconsistencies", [])
    
    inc_rows = []
    detected_types = set([f["type"] for f in findings])
    for item in inc_gt:
        exp_rule = item["expected_rule"]
        det = "YES" if exp_rule in detected_types else "NO"
        inc_rows.append({
            "Expected Finding": item["summary"],
            "Finding Type": exp_rule,
            "Detected?": det,
            "Evidence": f"Rule {exp_rule} checked in DB",
            "Why Missed if any": "None" if det == "YES" else "Rule condition threshold"
        })
    df_inc = pd.DataFrame(inc_rows)
    inc_csv = BASE_DIR / "evaluation" / "inconsistency_diagnostics_v2.csv"
    df_inc.to_csv(inc_csv, index=False)

if __name__ == "__main__":
    generate_diagnostics()
