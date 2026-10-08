from app.retrieval.citation import CitationValidator
from app.llm.client import LLMClient

def test_citation_formatting():
    chunks = [
        {
            "text": "SWC_SpeedSensor produces EngineSpeed_RPM",
            "similarity_score": 0.85,
            "metadata": {
                "document_id": "DOC-001",
                "document_name": "HLD_v1.0.pdf",
                "version_label": "v1.0",
                "page_number": 2,
                "section": "Interfaces",
                "chunk_id": "DOC-001-P02-C01"
            }
        }
    ]
    citations = CitationValidator.format_citations(chunks)
    assert len(citations) == 1
    assert citations[0]["citation_id"] == "Source 1"
    assert citations[0]["page"] == 2
    assert citations[0]["section"] == "Interfaces"

def test_deliberate_hallucination_detection():
    chunks = [
        {
            "text": "EngineSpeed_RPM is in range 0-8000.",
            "similarity_score": 0.90,
            "metadata": {"document_id": "DOC-01", "page_number": 1, "section": "Overview"}
        }
    ]
    # Answer with missing inline citation marker
    hallucinated_answer = "SWC_BatteryCharger controls high voltage grid connection."
    is_grounded, limitations = CitationValidator.validate_grounding(hallucinated_answer, chunks)
    assert any("missing explicit [Source X]" in lim for lim in limitations)

def test_provider_status_reporting():
    client = LLMClient()
    status = client.get_provider_status()
    assert "user_display" in status
    assert "requested_provider" in status
