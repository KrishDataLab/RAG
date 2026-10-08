import os
import sys
import json
import hashlib
import time
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.db.repositories import DatabaseRepository, SessionLocal
from app.retrieval.vector_store import MemoryVectorStore
from app.retrieval.retriever import ArchitectureRetriever
from app.llm.client import LLMClient
from app.evaluation.metrics import EvaluationMetricsCalculator
from app.retrieval.citation import CitationValidator
from app.llm.prompts import prompt_manager

def main():
    print("==================================================")
    print("   AHITA Frozen System Holdout Evaluation Suite   ")
    print("==================================================")

    db = SessionLocal()
    repo = DatabaseRepository(db)
    vector_store = MemoryVectorStore(load_existing=True)
    llm_client = LLMClient()
    retriever = ArchitectureRetriever(vector_store)

    holdout_file = BASE_DIR / "evaluation" / "holdout_questions_v1.jsonl"
    with open(holdout_file, "rb") as f:
        file_bytes = f.read()
        sha256_hash = hashlib.sha256(file_bytes).hexdigest()

    questions = []
    with open(holdout_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                questions.append(json.loads(line))

    ans_questions = [q for q in questions if q.get("is_answerable", True)]
    unans_questions = [q for q in questions if not q.get("is_answerable", True)]

    print("Ingesting sample AUTOSAR HLD documents into vector store...")
    from app.ingestion.pipeline import IngestionPipeline
    pipeline = IngestionPipeline(repo, vector_store)
    hld1 = BASE_DIR.parent / "Input_Data" / "T03_HLD_v1.0_EngineControl_v1.0.pdf"
    hld2 = BASE_DIR.parent / "Input_Data" / "T03_HLD_v1.1_EngineControl_v1.0.pdf"
    if hld1.exists():
        pipeline.run(file_path=str(hld1), project_id="P001", version_label="v1.0")
    if hld2.exists():
        pipeline.run(file_path=str(hld2), project_id="P001", version_label="v1.1")

    print(f"Holdout Dataset SHA256: {sha256_hash}")
    print(f"Total Holdout Questions: {len(questions)}")
    print(f"Answerable Questions: {len(ans_questions)} | Unanswerable Questions: {len(unans_questions)}")

    r1_hits, r3_hits, r5_hits, r8_hits = 0, 0, 0, 0
    per_q_recalls_r8 = []

    qa_outcomes = []
    grounded_flags = []
    citation_valid_flags = []
    total_latencies = []

    for q_item in questions:
        start_t = time.time()
        q_id = q_item["id"]
        q_text = q_item["question"]
        is_ans = q_item.get("is_answerable", True)
        exp_pages = q_item.get("expected_pages", [])
        exp_keywords = q_item.get("expected_keywords", [])

        # 1. Retrieve
        chunks = retriever.retrieve(query=q_text, top_k=8)
        ret_pages = [c["metadata"].get("page_number", 1) for c in chunks]

        # 2. Retrieval Recall
        if is_ans:
            h1 = any(p in exp_pages for p in ret_pages[:1])
            h3 = any(p in exp_pages for p in ret_pages[:3])
            h5 = any(p in exp_pages for p in ret_pages[:5])
            h8 = any(p in exp_pages for p in ret_pages[:8])

            if h1: r1_hits += 1
            if h3: r3_hits += 1
            if h5: r5_hits += 1
            if h8: r8_hits += 1

            rec8 = EvaluationMetricsCalculator.calculate_retrieval_recall(ret_pages[:8], exp_pages)
            per_q_recalls_r8.append(rec8)
        else:
            rec8 = 1.0

        # 3. Format citations & prompt
        context_str = ""
        for c in chunks:
            meta = c["metadata"]
            context_str += f"[Source 1] Page: {meta.get('page_number')}, Section: {meta.get('section')}\n{c['text']}\n\n"

        system_prompt = prompt_manager.get_prompt("rag_system_v1.txt")
        rag_prompt = prompt_manager.render("rag_answer_v1.txt", context=context_str or "No evidence available.", question=q_text)

        # 4. Generate Answer
        answer = llm_client.generate(prompt=rag_prompt, system_instruction=system_prompt)
        latency = time.time() - start_t
        total_latencies.append(latency)

        # 5. Grounding & Citation Validation
        is_grounded, limitations = CitationValidator.validate_grounding(answer, chunks)
        grounded_flags.append(1.0 if is_grounded else 0.0)
        has_citations = ("Source" in answer or "Page" in answer or not chunks or not is_ans)
        citation_valid_flags.append(1.0 if has_citations else 0.0)

        # 6. Classification
        ans_lower = answer.lower()
        is_abstained_msg = ("could not find" in ans_lower or "insufficient evidence" in ans_lower or "not found" in ans_lower)

        if is_ans:
            if is_abstained_msg:
                outcome = "INCORRECT_ABSTENTION"
            else:
                kw_matched = any(kw.lower() in ans_lower for kw in exp_keywords) if exp_keywords else True
                outcome = "CORRECT_ANSWER" if (is_grounded and kw_matched) else "INCORRECT_ANSWER"
        else:
            if is_abstained_msg:
                outcome = "CORRECT_ABSTENTION"
            else:
                outcome = "INCORRECT_ANSWER"

        qa_outcomes.append({
            "Question ID": q_id,
            "Question": q_text,
            "Category": q_item["category"],
            "Is Answerable": is_ans,
            "Outcome": outcome,
            "Is Grounded": is_grounded,
            "Has Citations": has_citations,
            "Latency Sec": round(latency, 3),
            "Answer Snippet": answer[:150] + "..."
        })

    # Summary Metrics
    ans_n = len(ans_questions)
    correct_ans_count = sum(1 for q in qa_outcomes if q["Is Answerable"] and q["Outcome"] == "CORRECT_ANSWER")
    answer_acc_pct = (correct_ans_count / ans_n) * 100.0

    r1_pct = (r1_hits / ans_n) * 100.0
    r3_pct = (r3_hits / ans_n) * 100.0
    r5_pct = (r5_hits / ans_n) * 100.0
    r8_pct = (r8_hits / ans_n) * 100.0
    mean_r8_pct = (sum(per_q_recalls_r8) / ans_n) * 100.0

    tot_n = len(questions)
    groundedness_pct = (sum(grounded_flags) / tot_n) * 100.0
    citation_indicator_rate = (sum(citation_valid_flags) / tot_n) * 100.0

    unans_n = len(unans_questions)
    correct_abastaintions = sum(1 for q in qa_outcomes if not q["Is Answerable"] and q["Outcome"] == "CORRECT_ABSTENTION")
    abstention_acc_pct = (correct_abastaintions / unans_n) * 100.0 if unans_n > 0 else 100.0

    print("\n==================================================")
    print("           UNSEEN HOLDOUT EVALUATION METRICS       ")
    print("==================================================")
    print(f"Holdout Answer Accuracy      : {answer_acc_pct:.2f}% ({correct_ans_count}/{ans_n})")
    print(f"Holdout Hits@1 / Recall@1    : {r1_hits}/{ans_n} = {r1_pct:.2f}%")
    print(f"Holdout Hits@3 / Recall@3    : {r3_hits}/{ans_n} = {r3_pct:.2f}%")
    print(f"Holdout Hits@5 / Recall@5    : {r5_hits}/{ans_n} = {r5_pct:.2f}%")
    print(f"Holdout Hits@8 / Recall@8    : {r8_hits}/{ans_n} = {r8_pct:.2f}%")
    print(f"Holdout Mean Recall@8        : {mean_r8_pct:.2f}%")
    print(f"Holdout Groundedness Rate    : {groundedness_pct:.2f}%")
    print(f"Holdout Citation Indicator Rate: {citation_indicator_rate:.2f}%")
    print(f"Holdout Abstention Accuracy  : {abstention_acc_pct:.2f}% ({correct_abastaintions}/{unans_n})")
    print("==================================================")

    # Save CSV
    out_csv = BASE_DIR / "evaluation" / "holdout_results_v1.csv"
    df = pd.DataFrame(qa_outcomes)
    df.to_csv(out_csv, index=False)
    print(f"\nExported {out_csv}")

if __name__ == "__main__":
    main()
