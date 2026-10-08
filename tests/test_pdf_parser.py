from app.core.config import BASE_DIR
from app.ingestion.pdf_parser import PDFParser

def test_pdf_parser_sample():
    sample_path = BASE_DIR.parent / "Input_Data" / "T03_HLD_v1.0_EngineControl_v1.0.pdf"
    parser = PDFParser()
    result = parser.parse_pdf(str(sample_path))
    assert result["page_count"] > 0
    assert "file_name" in result
    assert "sha256" in result
    assert len(result["pages"]) == result["page_count"]
