from fastapi.testclient import TestClient

from carecall_api import config
from carecall_api.main import app

client = TestClient(app)

SAMUEL_ID = "P-1008"  # Samuel Rivera - call_021 reports Gus's (his neighbor's) fall


def test_submit_feedback_on_an_answer():
    ask_response = client.post("/api/ask", json={"question": "What new medication did Margaret Chen start?"})
    request_id = ask_response.json()["request_id"]

    response = client.post(
        "/api/v1/feedback",
        json={
            "target_type": "answer",
            "target_id": request_id,
            "category": "correct",
            "actor": "coordinator_amy",
            "comment": "Matches the transcript.",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["feedback_id"]
    assert body["target_type"] == "answer"
    assert body["target_id"] == request_id
    assert body["category"] == "correct"
    assert body["actor"] == "coordinator_amy"
    assert body["comment"] == "Matches the transcript."


def test_submit_feedback_rejects_invalid_target_type():
    response = client.post(
        "/api/v1/feedback",
        json={"target_type": "not-a-real-type", "target_id": "req-1", "category": "correct", "actor": "amy"},
    )
    assert response.status_code == 422


def test_submit_feedback_rejects_category_not_valid_for_target_type():
    # "unsupported_claim" is an answer-only category, not valid for timeline_event.
    response = client.post(
        "/api/v1/feedback",
        json={
            "target_type": "timeline_event",
            "target_id": "evt-1",
            "category": "unsupported_claim",
            "actor": "amy",
        },
    )
    assert response.status_code == 422


def test_list_feedback_can_filter_by_target_type_and_category():
    ask_response = client.post("/api/ask", json={"question": "What new medication did Margaret Chen start?"})
    request_id = ask_response.json()["request_id"]
    client.post(
        "/api/v1/feedback",
        json={"target_type": "answer", "target_id": request_id, "category": "incorrect", "actor": "amy"},
    )

    response = client.get("/api/v1/feedback", params={"target_type": "answer", "category": "incorrect"})
    assert response.status_code == 200
    records = response.json()["feedback"]
    assert records
    assert all(r["target_type"] == "answer" and r["category"] == "incorrect" for r in records)


def test_feedback_summary_reflects_submitted_records():
    before = client.get("/api/v1/feedback/summary").json()
    ask_response = client.post("/api/ask", json={"question": "What new medication did Margaret Chen start?"})
    request_id = ask_response.json()["request_id"]
    client.post(
        "/api/v1/feedback",
        json={"target_type": "answer", "target_id": request_id, "category": "correct", "actor": "amy"},
    )

    after = client.get("/api/v1/feedback/summary").json()
    assert after["total"] == before["total"] + 1
    assert after["by_target_type"]["answer"] == before["by_target_type"].get("answer", 0) + 1
    assert after["by_category"]["correct"] == before["by_category"].get("correct", 0) + 1


def test_confirming_timeline_event_feedback_syncs_review_status():
    events = client.get(f"/api/v1/patients/{SAMUEL_ID}/timeline").json()["timeline_events"]
    target = next(e for e in events if e["event_type"] == "home_safety_concern")

    response = client.post(
        "/api/v1/feedback",
        json={
            "target_type": "timeline_event",
            "target_id": target["event_id"],
            "category": "confirm",
            "actor": "coordinator_amy",
        },
    )
    assert response.status_code == 200

    updated = client.get(f"/api/v1/patients/{SAMUEL_ID}/timeline").json()["timeline_events"]
    updated_target = next(e for e in updated if e["event_id"] == target["event_id"])
    assert updated_target["review_status"] == "confirmed"


def test_dismissing_pattern_feedback_syncs_reviewed_status():
    patterns = client.get(f"/api/v1/patients/{SAMUEL_ID}/patterns").json()["patterns"]
    assert patterns
    target = patterns[0]

    response = client.post(
        "/api/v1/feedback",
        json={
            "target_type": "pattern",
            "target_id": target["pattern_id"],
            "category": "dismiss",
            "actor": "coordinator_amy",
        },
    )
    assert response.status_code == 200

    updated = client.get(f"/api/v1/patients/{SAMUEL_ID}/patterns").json()["patterns"]
    updated_target = next(p for p in updated if p["pattern_id"] == target["pattern_id"])
    assert updated_target["reviewed_status"] == "dismissed"


def test_audit_record_feedback_summary_reflects_real_feedback(monkeypatch):
    monkeypatch.setattr(config, "DEVELOPER_MODE", True)
    ask_response = client.post("/api/ask", json={"question": "What new medication did Margaret Chen start?"})
    request_id = ask_response.json()["request_id"]

    record_before = client.get(f"/api/v1/audit/questions/{request_id}").json()
    assert record_before["feedback_summary"] == {"total": 0, "by_category": {}}

    client.post(
        "/api/v1/feedback",
        json={"target_type": "answer", "target_id": request_id, "category": "correct", "actor": "amy"},
    )

    record_after = client.get(f"/api/v1/audit/questions/{request_id}").json()
    assert record_after["feedback_summary"] == {"total": 1, "by_category": {"correct": 1}}
