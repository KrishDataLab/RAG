from app.ingestion.chunker import ContextAwareChunker

def test_chunker():
    chunker = ContextAwareChunker(chunk_size=100)
    parsed_pdf = {
        "file_name": "test.pdf",
        "pages": [
            {
                "page_number": 1,
                "section": "Section 1",
                "text": "SWC_SpeedSensor provides interface RTE_I_EngineSpeed. SWC_TorqueCalc consumes interface RTE_I_EngineSpeed."
            }
        ]
    }
    chunks = chunker.chunk_document(parsed_pdf, doc_id="DOC-TEST", version_label="v1.0")
    assert len(chunks) > 0
    assert chunks[0]["chunk_id"].startswith("DOC-TEST-P01-C01")
    assert chunks[0]["page_number"] == 1
