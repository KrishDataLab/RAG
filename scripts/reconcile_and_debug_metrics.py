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
from app.llm.client import LLMClient
from app.ingestion.pipeline import IngestionPipeline
from app.extraction.entities import EntityExtractor
from app.extraction.relationships import RelationshipExtractor
from app.comparison.diff import RevisionComparator
from app.evaluation.datasets import EvaluationDatasetLoader
from app.evaluation.runners import EvaluationRunner

def main():
    print("==================================================")
    print("   AHITA Capstone Metrics Reconciliation Suite   ")
    print("==================================================")

    db = SessionLocal()
    repo = DatabaseRepository(db)
    vector_store = VectorStore()
    llm_client = LLMClient()
    retriever = ArchitectureRetriever(vector_store)

    # 1. Ensure sample PDFs are ingested
    sample_v1 = BASE_DIR.parent / "Input_Data" / "T03_HLD_v1.0_EngineControl_v1.0.pdf"
    sample_v2 = BASE_DIR.parent / "Input_Data" / "T03_HLD_v1.1_EngineControl_v1.0.pdf"

    pipeline = IngestionPipeline(repo, vector_store)
    res_v1 = pipeline.run(file_path=str(sample_v1), project_id="P001", version_label="v1.0")
    res_v2 = pipeline.run(file_path=str(sample_v2), project_id="P001", version_label="v1.1")
    
    doc_v1_id = res_v1["document_id"]
    doc_v2_id = res_v2["document_id"]

    # Extract entities & relationships for BOTH Version A and Version B
    extractor = EntityExtractor(llm_client)
    rel_extractor = RelationshipExtractor(llm_client)

    # Version A
    chunks_rec_a = repo.get_chunks_by_document(doc_v1_id)
    chunks_data_a = [c.__dict__ for c in chunks_rec_a]
    for c in chunks_data_a: c.pop("_sa_instance_state", None)
    entities_a = extractor.extract_from_chunks(chunks_data_a)
    rels_a = rel_extractor.extract_relationships(chunks_data_a, entities_a)
    repo.save_entities_and_relationships(doc_v1_id, entities_a, rels_a)

    # Version B
    chunks_rec_b = repo.get_chunks_by_document(doc_v2_id)
    chunks_data_b = [c.__dict__ for c in chunks_rec_b]
    for c in chunks_data_b: c.pop("_sa_instance_state", None)
    entities_b = extractor.extract_from_chunks(chunks_data_b)
    rels_b = rel_extractor.extract_relationships(chunks_data_b, entities_b)
    repo.save_entities_and_relationships(doc_v2_id, entities_b, rels_b)

    comparator = RevisionComparator(repo, llm_client)
    comp_res = comparator.compare_documents(doc_v1_id, doc_v2_id, project_id="P001")

    # 2. Inspect Ground Truth vs Predictions
    gt_data = EvaluationDatasetLoader.load_inconsistency_ground_truth("v2")
    gt_list = gt_data.get("inconsistencies", [])
    gt_rules = [g["expected_rule"] for g in gt_list]

    print("\n--- 1. Ground Truth Inspection ---")
    print(f"Total ground-truth findings: {len(gt_rules)}")
    for g in gt_list:
        print(f"  Expected {g['expected_rule']}: {g['summary']}")

    db_findings = repo.get_findings("P001")
    pred_rules = [f["type"] for f in db_findings]
    unique_pred_types = set(pred_rules)
    unique_gt_types = set(gt_rules)

    tp_set = unique_pred_types & unique_gt_types
    fp_set = unique_pred_types - unique_gt_types
    fn_set = unique_gt_types - unique_pred_types

    tp = len(tp_set)
    fp = len(fp_set)
    fn = len(fn_set)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    print("\n--- 2. Evaluator Inconsistency Metrics Calculation ---")
    print(f"Ground Truth Count: {len(unique_gt_types)}")
    print(f"Prediction Count: {len(unique_pred_types)}")
    print(f"True Positives (TP): {tp} ({tp_set})")
    print(f"False Positives (FP): {fp} ({fp_set})")
    print(f"False Negatives (FN): {fn} ({fn_set})")
    print(f"Precision = TP / (TP + FP) = {tp} / ({tp} + {fp}) = {precision:.4f} ({precision*100:.1f}%)")
    print(f"Recall = TP / (TP + FN) = {tp} / ({tp} + {fn}) = {recall:.4f} ({recall*100:.1f}%)")
    print(f"F1 = 2 * P * R / (P + R) = {f1:.4f} ({f1*100:.1f}%)")

    # Debug CSV
    debug_rows = []
    for idx, g in enumerate(gt_list, start=1):
        rule = g["expected_rule"]
        matched_f = [f for f in db_findings if f["type"] == rule]
        matched_flag = "YES" if matched_f else "NO"
        det_id = matched_f[0]["id"] if matched_f else "N/A"
        det_type = matched_f[0]["type"] if matched_f else "N/A"

        debug_rows.append({
            "Expected Finding ID": f"GT-{idx:02d}",
            "Expected Type": rule,
            "Expected Summary": g["summary"],
            "Detected Finding ID": det_id,
            "Detected Type": det_type,
            "Matched?": matched_flag,
            "Reason if not matched": "None" if matched_flag == "YES" else "Rule condition omitted"
        })

    df_debug = pd.DataFrame(debug_rows)
    out_debug_csv = BASE_DIR / "evaluation" / "inconsistency_metrics_debug_v3.csv"
    df_debug.to_csv(out_debug_csv, index=False)
    print(f"\nExported {out_debug_csv}")

    # 3. Check Retrieval Metrics Consistency on 15 Answerable Questions
    questions = EvaluationDatasetLoader.load_benchmark_questions("v2")
    ans_questions = [q for q in questions if q.get("is_answerable", True)]
    unans_questions = [q for q in questions if not q.get("is_answerable", True)]

    r1_hits, r3_hits, r5_hits, r8_hits = 0, 0, 0, 0
    for item in ans_questions:
        q_text = item["question"]
        exp_pages = item.get("expected_pages", [])
        chunks = retriever.retrieve(query=q_text, top_k=8)
        ret_pages = [c["metadata"].get("page_number", 1) for c in chunks]

        if any(p in exp_pages for p in ret_pages[:1]):
            r1_hits += 1
        if any(p in exp_pages for p in ret_pages[:3]):
            r3_hits += 1
        if any(p in exp_pages for p in ret_pages[:5]):
            r5_hits += 1
        if any(p in exp_pages for p in ret_pages[:8]):
            r8_hits += 1

    ans_len = len(ans_questions)
    print("\n--- 3. Retrieval Metrics Consistency (Answerable Questions Only) ---")
    print(f"Answerable questions count: {ans_len}")
    print(f"Unanswerable questions count (Excluded from Retrieval Recall): {len(unans_questions)}")
    print(f"Hits@1: {r1_hits} / {ans_len} = {r1_hits / ans_len:.4f} ({r1_hits / ans_len * 100:.2f}%)")
    print(f"Hits@3: {r3_hits} / {ans_len} = {r3_hits / ans_len:.4f} ({r3_hits / ans_len * 100:.2f}%)")
    print(f"Hits@5: {r5_hits} / {ans_len} = {r5_hits / ans_len:.4f} ({r5_hits / ans_len * 100:.2f}%)")
    print(f"Hits@8: {r8_hits} / {ans_len} = {r8_hits / ans_len:.4f} ({r8_hits / ans_len * 100:.2f}%)")

    # 4. Generate Q&A Outcome Diagnostics
    runner = EvaluationRunner(retriever, llm_client, repo)
    eval_results = runner.run_benchmark(version="v2", project_id="P001")

    qa_outcomes = eval_results.get("qa_outcomes", [])
    df_qa = pd.DataFrame(qa_outcomes)
    out_qa_csv = BASE_DIR / "evaluation" / "qa_outcome_diagnostics_v3.csv"
    df_qa.to_csv(out_qa_csv, index=False)
    print(f"Exported {out_qa_csv}")

    outcome_counts = df_qa["outcome"].value_counts().to_dict()
    print("\n--- 4. Q&A Outcome Classification Breakdown ---")
    for outcome, count in outcome_counts.items():
        print(f"  {outcome:25s}: {count}")

    # Root EVALUATION_RESULTS.json & .csv
    root_json = BASE_DIR / "EVALUATION_RESULTS.json"
    root_csv = BASE_DIR / "EVALUATION_RESULTS.csv"
    with open(root_json, "w", encoding="utf-8") as f:
        json.dump(eval_results, f, indent=2)
    pd.DataFrame(eval_results.get("question_details", [])).to_csv(root_csv, index=False)

if __name__ == "__main__":
    main()
