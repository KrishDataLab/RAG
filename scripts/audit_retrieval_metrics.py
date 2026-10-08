import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.db.repositories import DatabaseRepository, SessionLocal
from app.retrieval.vector_store import VectorStore
from app.retrieval.retriever import ArchitectureRetriever
from app.evaluation.datasets import EvaluationDatasetLoader
from app.evaluation.metrics import EvaluationMetricsCalculator

def main():
    db = SessionLocal()
    repo = DatabaseRepository(db)
    vector_store = VectorStore()
    retriever = ArchitectureRetriever(vector_store)

    questions = EvaluationDatasetLoader.load_benchmark_questions("v2")
    ans_questions = [q for q in questions if q.get("is_answerable", True)]
    unans_questions = [q for q in questions if not q.get("is_answerable", True)]

    print(f"Total Questions: {len(questions)}")
    print(f"Answerable Questions = {len(ans_questions)}")
    print(f"Unanswerable Questions (Excluded from Retrieval Recall) = {len(unans_questions)}")

    r1_hits, r3_hits, r5_hits, r8_hits = 0, 0, 0, 0
    per_q_recalls_r8 = []

    for item in ans_questions:
        q_id = item["id"]
        q_text = item["question"]
        exp_pages = item.get("expected_pages", [])

        chunks = retriever.retrieve(query=q_text, top_k=8)
        ret_pages = [c["metadata"].get("page_number", 1) for c in chunks]

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

        print(f"  [{q_id}] Exp: {exp_pages} | Ret Pages[:8]: {ret_pages[:8]} | Hits@1:{h1} H@3:{h3} H@5:{h5} H@8:{h8} | Recall@8: {rec8:.2f}")

    n = len(ans_questions)
    print("\n--- Exact Audit Results ---")
    print(f"Answerable Questions = {n}")
    print(f"Hits@1 = {r1_hits} -> Recall@1 = {r1_hits}/{n} = {r1_hits/n*100:.2f}%")
    print(f"Hits@3 = {r3_hits} -> Recall@3 = {r3_hits}/{n} = {r3_hits/n*100:.2f}%")
    print(f"Hits@5 = {r5_hits} -> Recall@5 = {r5_hits}/{n} = {r5_hits/n*100:.2f}%")
    print(f"Hits@8 = {r8_hits} -> Recall@8 = {r8_hits}/{n} = {r8_hits/n*100:.2f}%")
    mean_r8 = sum(per_q_recalls_r8) / n
    print(f"Mean Recall@8 (Arithmetic Mean of Per-Q Recall) = {sum(per_q_recalls_r8):.2f}/{n} = {mean_r8*100:.2f}%")

if __name__ == "__main__":
    main()
