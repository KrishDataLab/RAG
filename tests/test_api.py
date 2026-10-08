import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from app.api.deps import get_llm_client
from app.api.main import app
from app.core.config import BASE_DIR
from app.llm.client import LLMClient

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data

def test_documents_list_endpoint():
    response = client.get("/api/v1/documents?project_id=P001")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_release_workflow_and_invalid_inputs():
    project_id = f"P_E2E_{uuid.uuid4().hex[:12]}"
    input_dir = BASE_DIR.parent / "Input_Data"
    revisions = [
        (input_dir / "T03_HLD_v1.0_EngineControl_v1.0.pdf", "v1.0"),
        (input_dir / "T03_HLD_v1.1_EngineControl_v1.0.pdf", "v1.1"),
    ]
    uploaded_paths = []
    previous_llm = app.dependency_overrides.get(get_llm_client)
    app.dependency_overrides[get_llm_client] = lambda: LLMClient(provider="fallback")

    try:
        document_ids = []
        for source_path, version_label in revisions:
            with source_path.open("rb") as source_file:
                upload = client.post(
                    "/api/v1/documents",
                    files={"file": (source_path.name, source_file, "application/pdf")},
                    data={"project_id": project_id, "version_label": version_label},
                )
            assert upload.status_code == 200
            uploaded_paths.append(Path(upload.json()["file_path"]))

            ingest = client.post(
                f"/api/v1/documents/release-{version_label}/ingest",
                data={
                    "file_path": upload.json()["file_path"],
                    "project_id": project_id,
                    "version_label": version_label,
                },
            )
            assert ingest.status_code == 200
            document_ids.append(ingest.json()["document_id"])

        answer = client.post(
            "/api/v1/query",
            json={
                "question": "Which component provides the RTE_I_EngineSpeed interface?",
                "project_id": project_id,
                "document_ids": [document_ids[0]],
                "top_k": 8,
            },
        )
        assert answer.status_code == 200
        assert answer.json()["citations"]
        assert "[Source" in answer.json()["answer"]

        unanswerable = client.post(
            "/api/v1/query",
            json={"question": "Does this ECU describe battery charging?", "project_id": project_id},
        )
        assert unanswerable.status_code == 200
        assert "could not find enough evidence" in unanswerable.json()["answer"].lower()

        for document_id in document_ids:
            extracted = client.post(f"/api/v1/documents/{document_id}/extract/entities")
            assert extracted.status_code == 200
            relationships = client.post(f"/api/v1/documents/{document_id}/extract/relationships")
            assert relationships.status_code == 200
            inventory = client.get(f"/api/v1/documents/{document_id}/architecture")
            assert inventory.status_code == 200
            assert inventory.json()["entities"]
            assert inventory.json()["relationships"]

        comparison = client.post(
            "/api/v1/compare",
            json={
                "document_a_id": document_ids[0],
                "document_b_id": document_ids[1],
                "project_id": project_id,
            },
        )
        assert comparison.status_code == 200
        assert comparison.json()["findings"]

        finding_id = comparison.json()["findings"][0]["id"]
        review = client.post(
            f"/api/v1/findings/{finding_id}/review",
            json={"status": "CONFIRMED", "reviewer_id": "release-test", "comment": "workflow test"},
        )
        assert review.status_code == 200

        evaluation = client.post(f"/api/v1/evaluation/run?project_id={project_id}")
        assert evaluation.status_code == 200
        assert evaluation.json()["summary"]["total_questions_tested"] > 0
        assert "citation_indicator_rate" in evaluation.json()["summary"]

        invalid_upload = client.post(
            "/api/v1/documents",
            files={"file": ("invalid-release-test.pdf", b"not a PDF", "application/pdf")},
            data={"project_id": project_id, "version_label": "invalid"},
        )
        assert invalid_upload.status_code == 200
        invalid_path = Path(invalid_upload.json()["file_path"])
        uploaded_paths.append(invalid_path)
        invalid_ingest = client.post(
            "/api/v1/documents/invalid-release-test/ingest",
            data={"file_path": str(invalid_path), "project_id": project_id, "version_label": "invalid"},
        )
        assert invalid_ingest.status_code == 400

        non_pdf = client.post(
            "/api/v1/documents",
            files={"file": ("release-test.txt", b"not a PDF", "text/plain")},
            data={"project_id": project_id, "version_label": "invalid"},
        )
        assert non_pdf.status_code == 400

        with revisions[0][0].open("rb") as source_file:
            traversed_upload = client.post(
                "/api/v1/documents",
                files={"file": ("../../release-traversal.pdf", source_file, "application/pdf")},
                data={"project_id": project_id, "version_label": "traversal"},
            )
        assert traversed_upload.status_code == 200
        assert ".." not in traversed_upload.json()["file_name"]
        uploaded_paths.append(Path(traversed_upload.json()["file_path"]))

        traversal_ingest = client.post(
            "/api/v1/documents/traversal/ingest",
            data={
                "file_path": str(BASE_DIR / "app" / "api" / "main.py"),
                "project_id": project_id,
                "version_label": "traversal",
            },
        )
        assert traversal_ingest.status_code == 400
        assert client.get("/api/v1/health").status_code == 200
    finally:
        if previous_llm is None:
            app.dependency_overrides.pop(get_llm_client, None)
        else:
            app.dependency_overrides[get_llm_client] = previous_llm
        for uploaded_path in uploaded_paths:
            uploaded_path.unlink(missing_ok=True)
