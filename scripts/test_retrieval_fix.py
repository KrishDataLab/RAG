import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.db.repositories import DatabaseRepository, SessionLocal
from app.retrieval.vector_store import VectorStore
from app.evaluation.datasets import EvaluationDatasetLoader
from app.evaluation.metrics import EvaluationMetricsCalculator

def main():
    db = SessionLocal()
    repo = DatabaseRepository(db)
    vs = VectorStore()

    questions = EvaluationDatasetLoader.load_benchmark_questions("v2")
    ans_questions = [q for q in questions if q.get("is_answerable", True)]

    # Get all chunks from vector store collection directly
    all_chunks = vs.collection.get()
    
    print(f"Total chunks in vector store: {len(all_chunks['ids'])}")

    for item in ans_questions:
        q_id = item["id"]
        q_text = item["question"]
        exp_pages = item["expected_pages"]

        # Vector search top 8
        raw_res = vs.search(query=q_text, top_k=8)
        raw_pages = [r["metadata"].get("page_number", 1) for r in raw_res]

        # Enhanced search: if vector search missed page, check keyword matching in collection text
        words = [w.strip("?,.") for w in q_text.split() if len(w.strip("?,.")) > 3 and w.lower() not in ["what", "which", "is", "there", "does", "the", "for", "with", "from", "between"]]
        
        keyword_hits = []
        for doc_id, text, meta in zip(all_chunks["ids"], all_chunks["documents"], all_chunks["metadatas"]):
            text_lower = text.lower()
            matches = sum(1 for w in words if w.lower() in text_lower)
            if matches > 0:
                keyword_hits.append((matches, meta.get("page_number", 1), doc_id, text))

        keyword_hits.sort(key=lambda x: x[0], reverse=True)
        kw_pages = [k[1] for k in keyword_hits]

        # Hybrid top 8
        hybrid_pages = []
        seen = set()
        for p in raw_pages[:4] + kw_pages[:4]:
            if p not in seen:
                seen.add(p)
                hybrid_pages.append(p)

        rec_raw = EvaluationMetricsCalculator.calculate_retrieval_recall(raw_pages, exp_pages)
        rec_hybrid = EvaluationMetricsCalculator.calculate_retrieval_recall(hybrid_pages, exp_pages)

        print(f"\n[{q_id}] {q_text}")
        print(f"  Expected: {exp_pages} | Raw Ret: {raw_pages[:4]} (Recall: {rec_raw:.2f}) | Hybrid Ret: {hybrid_pages[:4]} (Recall: {rec_hybrid:.2f})")

if __name__ == "__main__":
    main()
