import pytest
from fastapi.testclient import TestClient

from carecall_api import config
from carecall_api.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _enable_developer_mode(monkeypatch):
    monkeypatch.setattr(config, "DEVELOPER_MODE", True)
    yield


def test_audit_endpoints_are_forbidden_outside_developer_mode(monkeypatch):
    monkeypatch.setattr(config, "DEVELOPER_MODE", False)
    assert client.get("/api/v1/audit/questions").status_code == 403
    assert client.get("/api/v1/audit/questions/does-not-exist").status_code == 403


def test_asking_a_question_creates_a_retrievable_audit_record():
    ask_response = client.post("/api/ask", json={"question": "What new medication did Margaret Chen start?"})
    assert ask_response.status_code == 200
    request_id = ask_response.json()["request_id"]
    assert request_id

    audit_response = client.get(f"/api/v1/audit/questions/{request_id}")
    assert audit_response.status_code == 200
    record = audit_response.json()
    assert record["request_id"] == request_id
    assert record["answerable"] is True
    assert record["retrieval_mode"] == "hybrid"
    assert record["candidate_chunk_ids"]
    assert record["selected_evidence_ids"]
    assert record["final_citation_call_ids"]
    assert record["grounding_checks"]["citation_validation"] is True


def test_audit_record_never_contains_the_raw_question_text_by_default():
    ask_response = client.post("/api/ask", json={"question": "What new medication did Margaret Chen start?"})
    request_id = ask_response.json()["request_id"]

    record = client.get(f"/api/v1/audit/questions/{request_id}").json()
    assert record["question_preview"] is None
    assert record["question_hash"]
    assert len(record["question_hash"]) == 64  # sha256 hex digest


def test_unanswerable_question_audit_records_which_grounding_check_failed():
    ask_response = client.post("/api/ask", json={"question": "Did anyone mention chest pain?"})
    request_id = ask_response.json()["request_id"]

    record = client.get(f"/api/v1/audit/questions/{request_id}").json()
    assert record["answerable"] is False
    assert record["grounding_checks"] == {"answerability_gate": False}


def test_list_audit_questions_can_filter_by_answerable():
    client.post("/api/ask", json={"question": "What new medication did Margaret Chen start?"})
    client.post("/api/ask", json={"question": "Did anyone mention chest pain?"})

    unanswerable = client.get("/api/v1/audit/questions", params={"answerable": False})
    assert unanswerable.status_code == 200
    assert all(r["answerable"] is False for r in unanswerable.json()["audit_records"])


def test_get_unknown_audit_record_returns_404():
    response = client.get("/api/v1/audit/questions/does-not-exist")
    assert response.status_code == 404
