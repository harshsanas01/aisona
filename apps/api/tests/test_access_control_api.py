from fastapi.testclient import TestClient

from carecall_api.access_control import ROLE_HEADER_NAME
from carecall_api.main import app

client = TestClient(app)

SAMUEL_ID = "P-1008"


def _headers(role: str) -> dict:
    return {ROLE_HEADER_NAME: role}


def test_viewer_cannot_confirm_a_timeline_event():
    events = client.get(f"/api/v1/patients/{SAMUEL_ID}/timeline").json()["timeline_events"]
    event_id = events[0]["event_id"]
    response = client.patch(
        f"/api/v1/timeline-events/{event_id}", json={"review_status": "confirmed"}, headers=_headers("viewer"),
    )
    assert response.status_code == 403


def test_coordinator_can_confirm_a_timeline_event():
    events = client.get(f"/api/v1/patients/{SAMUEL_ID}/timeline").json()["timeline_events"]
    event_id = events[0]["event_id"]
    response = client.patch(
        f"/api/v1/timeline-events/{event_id}", json={"review_status": "confirmed"}, headers=_headers("coordinator"),
    )
    assert response.status_code == 200


def test_no_role_header_defaults_to_coordinator_permissions():
    """Preserves pre-RBAC behavior: a caller sending no role header at all
    (every pre-existing test, script, and not-yet-updated frontend build)
    keeps working exactly as before."""
    events = client.get(f"/api/v1/patients/{SAMUEL_ID}/timeline").json()["timeline_events"]
    event_id = events[0]["event_id"]
    response = client.patch(f"/api/v1/timeline-events/{event_id}", json={"review_status": "dismissed"})
    assert response.status_code == 200


def test_viewer_cannot_submit_feedback():
    response = client.post(
        "/api/v1/feedback",
        json={"target_type": "answer", "target_id": "req-1", "category": "correct", "actor": "viewer_user"},
        headers=_headers("viewer"),
    )
    assert response.status_code == 403


def test_viewer_cannot_create_a_task():
    response = client.post(
        "/api/v1/tasks",
        json={
            "title": "Call patient", "description": "Follow up", "patient_id": SAMUEL_ID,
            "category": "general_outreach",
        },
        headers=_headers("viewer"),
    )
    assert response.status_code == 403


def test_admin_can_create_a_task():
    response = client.post(
        "/api/v1/tasks",
        json={
            "title": "Call patient", "description": "Follow up", "patient_id": SAMUEL_ID,
            "category": "general_outreach",
        },
        headers=_headers("admin"),
    )
    assert response.status_code == 201


def test_viewer_can_still_read_the_timeline():
    """RBAC only restricts mutations - every role can view."""
    response = client.get(f"/api/v1/patients/{SAMUEL_ID}/timeline", headers=_headers("viewer"))
    assert response.status_code == 200


def test_unknown_role_header_is_treated_as_having_no_permissions():
    events = client.get(f"/api/v1/patients/{SAMUEL_ID}/timeline").json()["timeline_events"]
    event_id = events[0]["event_id"]
    response = client.patch(
        f"/api/v1/timeline-events/{event_id}", json={"review_status": "confirmed"},
        headers=_headers("not-a-real-role"),
    )
    assert response.status_code == 403


def test_viewer_cannot_generate_a_brief():
    response = client.post(
        "/api/v1/briefs", json={"type": "daily"}, headers=_headers("viewer"),
    )
    assert response.status_code == 403


def test_viewer_cannot_rebuild_person_mentions():
    response = client.post(
        f"/api/v1/patients/{SAMUEL_ID}/people/rebuild", headers=_headers("viewer"),
    )
    assert response.status_code == 403
