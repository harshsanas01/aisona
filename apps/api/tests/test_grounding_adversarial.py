import json
from pathlib import Path

import pytest

from carecall_api.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

ADVERSARIAL_PATH = Path(__file__).resolve().parents[3] / "data" / "evaluation" / "adversarial_questions.json"
ADVERSARIAL_QUESTIONS = json.loads(ADVERSARIAL_PATH.read_text())["questions"]


@pytest.mark.parametrize("question", ADVERSARIAL_QUESTIONS, ids=[q["id"] for q in ADVERSARIAL_QUESTIONS])
def test_adversarial_question(question):
    response = client.post("/api/ask", json={"question": question["question"]})
    assert response.status_code == 200
    body = response.json()

    assert body["answerable"] is question["expected_answerable"]

    if not body["answerable"]:
        assert body["citations"] == []
        assert body["answer"] == (
            "The care-call transcripts do not contain enough evidence to answer this question."
        )

    cited = {c["call_id"] for c in body["citations"]}

    for expected_call in question.get("expected_source_calls", []):
        assert expected_call in cited, f"expected {expected_call} in citations, got {cited}"

    for forbidden_call in question.get("forbidden_source_calls", []):
        assert forbidden_call not in cited, f"{forbidden_call} must not be cited, got {cited}"
