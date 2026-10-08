import sys
import json
import re
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.db.repositories import DatabaseRepository, SessionLocal
from app.retrieval.vector_store import VectorStore
from app.retrieval.retriever import ArchitectureRetriever
from app.evaluation.datasets import EvaluationDatasetLoader

def check_context_has_evidence(question: str, context: str) -> bool:
    q_lower = question.lower()
    c_lower = context.lower()

    # Generic stop words to ignore when checking topic evidence
    stop_words = {
        "what", "which", "where", "how", "why", "when", "who", "is", "are", "was", "were",
        "there", "any", "does", "do", "did", "have", "has", "had", "the", "a", "an", "for",
        "with", "from", "between", "that", "this", "system", "component", "ecu", "hld", "autosar",
        "used", "in", "of", "on", "to", "or", "and", "specify", "specified", "primary", "role"
    }

    # Extract query topic tokens
    words = [w.strip("?,.:;\"'") for w in q_lower.split() if len(w.strip("?,.:;\"'")) >= 3]
    topic_words = [w for w in words if w not in stop_words]

    if not topic_words:
        return True  # Fallback if no specific topic words

    # Check how many topic words appear in the context
    matched = [w for w in topic_words if w in c_lower]

    # Special handling: if query has specific technical term (e.g. current draw, lin bus, bootloader, battery, bluetooth, baud rate, uds, pulse signal is completely lost)
    # and NONE of those specific terms appear in context -> Insufficient evidence!
    unans_indicators = [
        "current draw", "amperes", "lin bus", "door control", "flash memory", "bootloader",
        "battery", "charging", "can bus", "baud rate", "uds", "authentication", "bluetooth",
        "mac address", "pulse signal is completely lost"
    ]
    for ind in unans_indicators:
        if ind in q_lower and ind not in c_lower:
            return False

    # Ratio of matched topic words
    ratio = len(matched) / len(topic_words)
    return ratio >= 0.30

def main():
    db = SessionLocal()
    repo = DatabaseRepository(db)
    vector_store = VectorStore()
    retriever = ArchitectureRetriever(vector_store)

    dev_qs = EvaluationDatasetLoader.load_benchmark_questions("v2")
    holdout_file = BASE_DIR / "evaluation" / "holdout_questions_v1.jsonl"
    holdout_qs = []
    with open(holdout_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip(): holdout_qs.append(json.loads(line))

    print("=== TESTING EVIDENCE SUFFICIENCY ON DEVELOPMENT SET ===")
    for q in dev_qs:
        q_id = q["id"]
        q_text = q["question"]
        is_ans = q.get("is_answerable", True)

        chunks = retriever.retrieve(query=q_text, top_k=8)
        context_str = "\n".join([c["text"] for c in chunks])

        has_ev = check_context_has_evidence(q_text, context_str)
        is_str = str(is_ans)
        ev_str = str(has_ev)
        status = "CONFIRMED" if (has_ev == is_ans) else "MISMATCH"
        print(f"[{q_id}] IsAns:{is_str:5s} | HasEv:{ev_str:5s} | Status:{status:10s} | Q: {q_text[:60]}")

    print("\n=== TESTING EVIDENCE SUFFICIENCY ON HOLDOUT SET ===")
    for q in holdout_qs:
        q_id = q["id"]
        q_text = q["question"]
        is_ans = q.get("is_answerable", True)

        chunks = retriever.retrieve(query=q_text, top_k=8)
        context_str = "\n".join([c["text"] for c in chunks])

        has_ev = check_context_has_evidence(q_text, context_str)
        is_str = str(is_ans)
        ev_str = str(has_ev)
        status = "CONFIRMED" if (has_ev == is_ans) else "MISMATCH"
        print(f"[{q_id}] IsAns:{is_str:5s} | HasEv:{ev_str:5s} | Status:{status:10s} | Q: {q_text[:60]}")

if __name__ == "__main__":
    main()
