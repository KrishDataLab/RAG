import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.retrieval.vector_store import VectorStore

def main():
    vs = VectorStore()
    all_chunks = vs.collection.get()
    print(f"Total chunks in vector store collection: {len(all_chunks['ids'])}")

    for c_id, text, meta in zip(all_chunks["ids"], all_chunks["documents"], all_chunks["metadatas"]):
        print(f"ID: {c_id:30s} | Doc: {meta.get('document_id')} | Page: {meta.get('page_number')} | Section: {meta.get('section')}")
        print(f"   Snippet: {text[:80]}...\n")

if __name__ == "__main__":
    main()
