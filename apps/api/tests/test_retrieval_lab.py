import pytest
from fastapi.testclient import TestClient

from carecall_api import config
from carecall_api.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _enable_developer_mode(monkeypatch):
    monkeypatch.setattr(config, "DEVELOPER_MODE", True)
    yield


def test_retrieval_lab_is_forbidden_outside_developer_mode(monkeypatch):
    monkeypatch.setattr(config, "DEVELOPER_MODE", False)
    response = client.post("/api/v1/retrieval-lab/compare", json={"question": "lisinopril"})
    assert response.status_code == 403


def test_compare_returns_all_four_modes_with_real_candidates():
    response = client.post(
        "/api/v1/retrieval-lab/compare", json={"question": "What new medication did Margaret Chen start?"},
    )
    assert response.status_code == 200
    body = response.json()
    modes = [r["mode"] for r in body["results"]]
    assert modes == ["lexical", "semantic", "hybrid", "hybrid_rerank"]
    for result in body["results"]:
        assert result["candidates"]
        for candidate in result["candidates"]:
            assert candidate["call_id"]
            assert candidate["quote"]


def test_hybrid_rerank_is_flagged_and_others_are_not():
    response = client.post("/api/v1/retrieval-lab/compare", json={"question": "lisinopril"})
    body = response.json()
    by_mode = {r["mode"]: r for r in body["results"]}
    assert by_mode["hybrid_rerank"]["reranked"] is True
    assert by_mode["hybrid"]["reranked"] is False
    assert by_mode["lexical"]["lexical_weight"] == 1.0
    assert by_mode["semantic"]["semantic_weight"] == 1.0


def test_compare_can_filter_by_patient_id():
    response = client.post(
        "/api/v1/retrieval-lab/compare", json={"question": "medication", "patient_id": "P-1001"},
    )
    assert response.status_code == 200
    for result in response.json()["results"]:
        assert all(c["patient_id"] == "P-1001" for c in result["candidates"])


def test_compare_rejects_invalid_date_range():
    response = client.post(
        "/api/v1/retrieval-lab/compare",
        json={"question": "lisinopril", "start_date": "2026-06-01", "end_date": "2026-01-01"},
    )
    assert response.status_code == 422


def test_compare_out_of_domain_question_returns_no_candidates():
    response = client.post("/api/v1/retrieval-lab/compare", json={"question": "What is the price of Bitcoin?"})
    assert response.status_code == 200
    for result in response.json()["results"]:
        assert result["candidates"] == []
