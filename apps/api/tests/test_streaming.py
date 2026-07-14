import json

from fastapi.testclient import TestClient

from carecall_api.main import app

client = TestClient(app)


def _parse_sse(body: str):
    events = []
    for block in body.strip().split("\n\n"):
        if not block.strip():
            continue
        event_name = "message"
        data = {}
        for line in block.split("\n"):
            if line.startswith("event: "):
                event_name = line[len("event: "):]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: "):])
        events.append((event_name, data))
    return events


def test_stream_supported_question_emits_full_event_sequence():
    response = client.post("/api/ask/stream", json={"question": "What new medication did Margaret Chen start?"})
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    events = _parse_sse(response.text)
    event_names = [name for name, _ in events]

    assert event_names[0] == "retrieval_started"
    assert "retrieval_completed" in event_names
    assert event_names.count("answer_delta") >= 1
    assert "citations" in event_names
    assert event_names[-1] == "completed"

    retrieval_completed = next(data for name, data in events if name == "retrieval_completed")
    assert retrieval_completed["candidate_count"] > 0

    citations_event = next(data for name, data in events if name == "citations")
    assert citations_event["citations"]
    assert citations_event["citations"][0]["call_id"] == "call_003"

    completed = next(data for name, data in events if name == "completed")
    assert completed["answerable"] is True


def test_stream_unanswerable_question_has_no_citations():
    response = client.post("/api/ask/stream", json={"question": "Did anyone mention chest pain?"})
    assert response.status_code == 200
    events = _parse_sse(response.text)

    citations_event = next(data for name, data in events if name == "citations")
    assert citations_event["citations"] == []

    completed = next(data for name, data in events if name == "completed")
    assert completed["answerable"] is False
    assert completed["confidence"] == "low"


def test_stream_invalid_date_range_emits_error_event():
    response = client.post("/api/ask/stream", json={
        "question": "Who has been having trouble sleeping?",
        "start_date": "2026-06-30",
        "end_date": "2026-06-01",
    })
    assert response.status_code == 200
    events = _parse_sse(response.text)
    assert events[0][0] == "error"


def test_stream_empty_question_returns_422():
    response = client.post("/api/ask/stream", json={"question": "   "})
    assert response.status_code == 422
