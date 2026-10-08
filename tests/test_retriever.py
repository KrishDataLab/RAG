from app.retrieval.vector_store import MemoryVectorStore
from app.retrieval.retriever import ArchitectureRetriever

def test_vector_store_and_retriever():
    vs = MemoryVectorStore()
    chunks = [
        {
            "chunk_id": "C-01",
            "document_id": "DOC-01",
            "document_name": "HLD_v1.pdf",
            "version_label": "v1.0",
            "page_number": 1,
            "section": "Overview",
            "text": "SWC_SpeedSensor calculates engine speed RPM.",
            "source_type": "HLD",
            "project_id": "P001"
        }
    ]
    vs.add_chunks(chunks)
    retriever = ArchitectureRetriever(vs)
    results = retriever.retrieve(query="engine speed RPM", top_k=1, project_id="P001")
    assert len(results) == 1
    assert results[0]["metadata"]["chunk_id"] == "C-01"
    assert results[0]["similarity_score"] > 0
