import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.retrieval.vector_store import VectorStore

def main():
    vs = VectorStore()
    queries = [
        "What signal is carried by port PPort_EngineSpeed?",
        "What interface does SWC_TorqueCalc provide to SWC_ThrottleActuator?",
        "What range and resolution is specified for signal EngineSpeed_RPM?",
        "What port type is PPort_ThrottleCmd?",
        "What RPort is owned by SWC_ThrottleActuator?",
        "Which safety standard is referenced by SWC_SafetyMonitor?",
        "What is the signal carried by RPort_SafetyCheck?"
    ]

    for q in queries:
        print(f"\nQUERY: {q}")
        res = vs.search(query=q, top_k=8)
        for idx, r in enumerate(res, 1):
            meta = r['metadata']
            print(f"  [{idx}] Score: {r['similarity_score']:.4f} | Page: {meta.get('page_number')} | Section: {meta.get('section')}")
            print(f"      Text: {r['text'][:100]}...")

if __name__ == "__main__":
    main()
