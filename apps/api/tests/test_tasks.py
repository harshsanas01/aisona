from fastapi.testclient import TestClient

from carecall_api.main import app

client = TestClient(app)

MARGARET_ID = "P-1001"
SAMUEL_ID = "P-1008"


def _create_task(**overrides):
    payload = {
        "title": "Call about medication",
        "description": "Follow up on lisinopril start.",
        "patient_id": MARGARET_ID,
        "category": "medication_review",
        "priority": "high",
        "created_by": "coordinator_amy",
    }
    payload.update(overrides)
    return client.post("/api/v1/tasks", json=payload)


def test_create_task_returns_201_with_open_status():
    response = _create_task()
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "open"
    assert body["is_suggested"] is False
    assert body["created_by"] == "coordinator_amy"


def test_create_task_rejects_invalid_category():
    response = _create_task(category="not-a-real-category")
    assert response.status_code == 422


def test_create_task_rejects_invalid_priority():
    response = _create_task(priority="urgent-ish")
    assert response.status_code == 422


def test_get_task_includes_activity_history():
    task = _create_task().json()
    response = client.get(f"/api/v1/tasks/{task['task_id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["task"]["task_id"] == task["task_id"]
    assert len(body["activity"]) == 1
    assert body["activity"][0]["action"] == "created"
    assert body["activity"][0]["to_status"] == "open"


def test_get_unknown_task_returns_404():
    response = client.get("/api/v1/tasks/does-not-exist")
    assert response.status_code == 404


def test_list_tasks_filters_by_patient_and_status():
    task = _create_task().json()
    response = client.get("/api/v1/tasks", params={"patient_id": MARGARET_ID, "status": "open"})
    assert response.status_code == 200
    ids = [t["task_id"] for t in response.json()["tasks"]]
    assert task["task_id"] in ids


def test_status_transition_from_blocked_to_completed_is_rejected():
    task = _create_task().json()
    task_id = task["task_id"]

    blocked = client.patch(f"/api/v1/tasks/{task_id}", json={"status": "blocked", "actor": "coordinator_amy"})
    assert blocked.status_code == 200
    assert blocked.json()["status"] == "blocked"

    rejected = client.post(f"/api/v1/tasks/{task_id}/complete")
    assert rejected.status_code == 422


def test_complete_then_reopen_round_trip():
    task = _create_task().json()
    task_id = task["task_id"]

    completed = client.post(f"/api/v1/tasks/{task_id}/complete")
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert completed.json()["completed_at"] is not None

    reopened = client.post(f"/api/v1/tasks/{task_id}/reopen")
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "open"
    assert reopened.json()["completed_at"] is None


def test_update_unknown_task_returns_404():
    response = client.patch("/api/v1/tasks/does-not-exist", json={"status": "in_progress"})
    assert response.status_code == 404


def test_suggest_task_from_gus_fall_event_is_grounded_and_not_attributed_to_samuel():
    timeline = client.get(f"/api/v1/patients/{SAMUEL_ID}/timeline").json()["timeline_events"]
    gus_event = next(e for e in timeline if e["event_type"] == "home_safety_concern")

    response = client.post(f"/api/v1/timeline-events/{gus_event['event_id']}/suggest-task")
    assert response.status_code == 200
    task = response.json()
    assert task["is_suggested"] is True
    assert task["created_by"] == "system"
    assert task["source_event_id"] == gus_event["event_id"]
    assert task["source_call_id"] == "call_021"
    assert "Samuel" not in task["description"]
    assert "caused" not in task["description"].lower()


def test_suggest_task_is_idempotent():
    timeline = client.get(f"/api/v1/patients/{MARGARET_ID}/timeline").json()["timeline_events"]
    event = next(e for e in timeline if e["event_type"] == "medication_started")

    first = client.post(f"/api/v1/timeline-events/{event['event_id']}/suggest-task")
    second = client.post(f"/api/v1/timeline-events/{event['event_id']}/suggest-task")
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["task_id"] == second.json()["task_id"]


def test_suggest_task_for_unknown_event_returns_404():
    response = client.post("/api/v1/timeline-events/does-not-exist/suggest-task")
    assert response.status_code == 404


def test_suggest_task_for_issue_resolved_event_returns_422():
    """issue_resolved events never generate a suggestion - the concern is
    already reported resolved, so no fresh outreach is implied."""
    found_resolved = False
    for patient_id in ["P-1006"]:  # Harold Okafor's pillbox resolution (call_020)
        timeline = client.get(f"/api/v1/patients/{patient_id}/timeline").json()["timeline_events"]
        for event in timeline:
            if event["event_type"] == "issue_resolved":
                found_resolved = True
                response = client.post(f"/api/v1/timeline-events/{event['event_id']}/suggest-task")
                assert response.status_code == 422
    assert found_resolved, "expected the Harold Okafor fixture to contain an issue_resolved event"
