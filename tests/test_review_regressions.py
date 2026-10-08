from pathlib import Path
import uuid

from fastapi.testclient import TestClient

from app.api.main import app
from app.core.config import BASE_DIR
from app.llm.client import LLMClient
from app.retrieval.citation import CitationValidator


client = TestClient(app)
ABSTENTION = "I could not find enough evidence in the indexed HLD documents to answer this confidently."


def _rag_prompt(question: str, *sources: str) -> str:
    context = "\n\n".join(
        f"[Source {index}] Document: test.pdf, Page: {index}, Section: Interfaces\n{text}"
        for index, text in enumerate(sources, start=1)
    )
    return f"CONTEXT EVIDENCE CHUNKS:\n{context}\n\nUSER QUESTION:\n{question}"


def _chunk(text: str) -> dict:
    return {"text": text, "metadata": {"document_id": "DOC-1", "page_number": 1}}


def test_fallback_returns_verbatim_matching_evidence():
    evidence = "SWC_SpeedSensor provides interface RTE_I_EngineSpeed."
    answer = LLMClient(provider="fallback").generate(
        _rag_prompt("Which component provides the RTE_I_EngineSpeed interface?", evidence)
    )

    assert evidence in answer
    assert "[Source 1]" in answer
    assert CitationValidator.validate_grounding(answer, [_chunk(evidence)])[0]


def test_fallback_abstains_when_known_keyword_has_unrelated_evidence():
    answer = LLMClient(provider="fallback").generate(
        _rag_prompt(
            "Which component provides the RTE_I_EngineSpeed interface?",
            "The system has a central gateway for diagnostics.",
        )
    )

    assert ABSTENTION in answer


def test_fallback_abstains_for_unknown_identifier_and_similar_wording():
    client_llm = LLMClient(provider="fallback")
    unknown_entity_answer = client_llm.generate(
        _rag_prompt(
            "What does RTE_I_UnknownControl provide?",
            "SWC_SpeedSensor provides interface RTE_I_EngineSpeed.",
        )
    )
    similar_wording_answer = client_llm.generate(
        _rag_prompt(
            "Who owns the throttle command?",
            "The actuator uses a throttle angle input to calculate torque.",
        )
    )
    entities_question_answer = client_llm.generate(
        _rag_prompt(
            "Which entities provide RTE_I_UnknownControl?",
            "SWC_SpeedSensor provides interface RTE_I_EngineSpeed.",
        )
    )

    assert ABSTENTION in unknown_entity_answer
    assert ABSTENTION in similar_wording_answer
    assert ABSTENTION in entities_question_answer


def test_fallback_reports_conflicting_evidence_without_choosing():
    evidence_a = "SWC_SpeedSensor provides interface RTE_I_EngineSpeed."
    evidence_b = "SWC_SpeedSensor_V2 provides interface RTE_I_EngineSpeed."
    answer = LLMClient(provider="fallback").generate(
        _rag_prompt(
            "Which component provides the RTE_I_EngineSpeed interface?",
            evidence_a,
            evidence_b,
        )
    )

    assert evidence_a in answer
    assert evidence_b in answer
    assert "[Source 1]" in answer
    assert "[Source 2]" in answer


def test_citation_validator_rejects_missing_or_unsupported_citations():
    evidence = _chunk("SWC_SpeedSensor provides interface RTE_I_EngineSpeed.")

    missing_citation, missing_reasons = CitationValidator.validate_grounding(
        "SWC_SpeedSensor provides interface RTE_I_EngineSpeed.", [evidence]
    )
    unrelated_evidence, _ = CitationValidator.validate_grounding(
        "SWC_BatteryCharger controls high voltage. [Source 1]",
        [_chunk("The diagnostic gateway records system events.")],
    )
    fabricated_source, _ = CitationValidator.validate_grounding(
        "SWC_SpeedSensor provides interface RTE_I_EngineSpeed. [Source 2]",
        [evidence],
    )

    assert not missing_citation
    assert any("missing explicit [Source X]" in reason for reason in missing_reasons)
    assert not unrelated_evidence
    assert not fabricated_source


def test_citation_validator_checks_every_claim_and_actual_source():
    chunks = [
        _chunk("SWC_SpeedSensor provides interface RTE_I_EngineSpeed."),
        _chunk("SWC_TorqueCalc consumes interface RTE_I_EngineSpeed."),
    ]
    supported = (
        "SWC_SpeedSensor provides interface RTE_I_EngineSpeed. [Source 1]\n"
        "SWC_TorqueCalc consumes interface RTE_I_EngineSpeed. [Source 2]"
    )
    partly_unsupported = (
        "SWC_SpeedSensor provides interface RTE_I_EngineSpeed. [Source 1]\n"
        "SWC_BatteryCharger controls high voltage. [Source 2]"
    )
    wrong_source = (
        "SWC_SpeedSensor provides interface RTE_I_EngineSpeed. [Source 2]"
    )

    assert CitationValidator.validate_grounding(supported, chunks)[0]
    assert not CitationValidator.validate_grounding(partly_unsupported, chunks)[0]
    assert not CitationValidator.validate_grounding(wrong_source, chunks)[0]


def test_uploads_with_same_name_do_not_overwrite_each_other():
    saved_paths = []
    project_id = f"P_UPLOAD_{uuid.uuid4().hex[:8]}"
    try:
        uploads = []
        for version_label, content in (
            ("v1.0", b"%PDF-1.4 first"),
            ("v1.1", b"%PDF-1.4 second"),
        ):
            response = client.post(
                "/api/v1/documents",
                files={"file": ("same-name.pdf", content, "application/pdf")},
                data={"project_id": project_id, "version_label": version_label},
            )
            assert response.status_code == 200
            uploads.append(response.json())
            saved_paths.append(Path(uploads[-1]["file_path"]))

        assert saved_paths[0] != saved_paths[1]
        assert saved_paths[0].read_bytes() == b"%PDF-1.4 first"
        assert saved_paths[1].read_bytes() == b"%PDF-1.4 second"
        assert [upload["version_label"] for upload in uploads] == ["v1.0", "v1.1"]
    finally:
        for path in saved_paths:
            path.unlink(missing_ok=True)


def test_identical_uploads_deduplicate_during_ingestion():
    source_path = BASE_DIR.parent / "Input_Data" / "T03_HLD_v1.0_EngineControl_v1.0.pdf"
    project_id = f"P_DUP_{uuid.uuid4().hex[:10]}"
    saved_paths = []

    try:
        uploads = []
        for _ in range(2):
            with source_path.open("rb") as source:
                response = client.post(
                    "/api/v1/documents",
                    files={"file": (source_path.name, source, "application/pdf")},
                    data={"project_id": project_id, "version_label": "v1.0"},
                )
            assert response.status_code == 200
            uploads.append(response.json())
            saved_paths.append(Path(response.json()["file_path"]))

        first = client.post(
            "/api/v1/documents/first/ingest",
            data={"file_path": uploads[0]["file_path"], "project_id": project_id, "version_label": "v1.0"},
        )
        second = client.post(
            "/api/v1/documents/second/ingest",
            data={"file_path": uploads[1]["file_path"], "project_id": project_id, "version_label": "v1.0"},
        )

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["document_id"] == second.json()["document_id"]
        assert second.json()["status"] == "ALREADY_EXISTS"
    finally:
        for path in saved_paths:
            path.unlink(missing_ok=True)
