import sys
import json
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.db.repositories import DatabaseRepository, SessionLocal
from app.retrieval.vector_store import VectorStore
from app.retrieval.retriever import ArchitectureRetriever
from app.llm.client import LLMClient
from app.evaluation.datasets import EvaluationDatasetLoader
from app.evaluation.metrics import EvaluationMetricsCalculator

def main():
    db = SessionLocal()
    repo = DatabaseRepository(db)
    vector_store = VectorStore()
    llm_client = LLMClient()
    retriever = ArchitectureRetriever(vector_store)

    questions = EvaluationDatasetLoader.load_benchmark_questions("v2")
    
    print(f"Total benchmark questions loaded: {len(questions)}")
    for q in questions:
        q_id = q["id"]
        q_text = q["question"]
        is_ans = q.get("is_answerable", True)
        exp_pages = q.get("expected_pages", [])
        exp_keywords = q.get("expected_keywords", [])

        chunks = retriever.retrieve(query=q_text, top_k=8)
        ret_pages = [c["metadata"].get("page_number", 1) for c in chunks]

        recall_score = EvaluationMetricsCalculator.calculate_retrieval_recall(ret_pages, exp_pages) if is_ans else 1.0

        # Construct prompt
        context_str = ""
        for c in chunks:
            meta = c["metadata"]
            context_str += f"[Source 1] Page: {meta.get('page_number')}, Section: {meta.get('section')}\n{c['text']}\n\n"

        prompt = f"CONTEXT EVIDENCE CHUNKS:\n{context_str}\n\nUSER QUESTION:\n{q_text}"
        answer = llm_client.generate(prompt=prompt)

        # Check keyword presence in generated answer
        ans_lower = answer.lower()
        matched_kw = [kw for kw in exp_keywords if kw.lower() in ans_lower]
        kw_pass = len(matched_kw) > 0 if exp_keywords else True

        print(f"\n[{q_id}] {q_text}")
        print(f"  Is Answerable: {is_ans}")
        print(f"  Expected Pages: {exp_pages} | Retrieved Pages: {ret_pages[:4]}")
        print(f"  Page Recall@K: {recall_score:.2f}")
        print(f"  Expected Keywords: {exp_keywords}")
        print(f"  Matched Keywords: {matched_kw}")
        print(f"  Answer Snippet: {answer[:200]}...")

if __name__ == "__main__":
    main()
