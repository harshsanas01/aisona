from fastapi.testclient import TestClient

from carecall_api.main import app

client = TestClient(app)

SAMUEL_ID = "P-1008"  # Samuel Rivera - call_021 reports Gus's (his neighbor's) fall


def test_get_patient_returns_summary():
    response = client.get(f"/api/v1/patients/{SAMUEL_ID}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == SAMUEL_ID
    assert body["name"] == "Samuel Rivera"
    assert body["timeline_event_count"] >= 2
    assert "unreviewed_event_count" in body


def test_get_unknown_patient_returns_404():
    response = client.get("/api/v1/patients/does-not-exist")
    assert response.status_code == 404


def test_get_patient_timeline_shape_and_gus_not_attributed_to_samuel():
    response = client.get(f"/api/v1/patients/{SAMUEL_ID}/timeline")
    assert response.status_code == 200
    body = response.json()
    events = body["timeline_events"]
    assert events
    assert set(events[0].keys()) == {
        "event_id", "patient_id", "event_type", "title", "description", "observed_date",
        "source_call_id", "source_turn_start", "source_turn_end", "quote", "confidence",
        "extraction_method", "review_status", "created_at", "updated_at",
    }

    home_safety = [e for e in events if e["event_type"] == "home_safety_concern"]
    assert home_safety
    for event in home_safety:
        assert event["patient_id"] == SAMUEL_ID
        assert "Gus" in event["quote"]
        assert "Samuel" not in event["quote"]


def test_get_patient_timeline_can_filter_by_event_type():
    response = client.get(f"/api/v1/patients/{SAMUEL_ID}/timeline", params={"event_type": "home_safety_concern"})
    assert response.status_code == 200
    events = response.json()["timeline_events"]
    assert events
    assert all(e["event_type"] == "home_safety_concern" for e in events)


def test_get_timeline_for_unknown_patient_returns_404():
    response = client.get("/api/v1/patients/does-not-exist/timeline")
    assert response.status_code == 404


def test_update_review_status_then_rebuild_preserves_it():
    events_before = client.get(f"/api/v1/patients/{SAMUEL_ID}/timeline").json()["timeline_events"]
    target = next(e for e in events_before if e["event_type"] == "home_safety_concern")

    patch_response = client.patch(
        f"/api/v1/timeline-events/{target['event_id']}",
        json={"review_status": "confirmed", "title": "Confirmed: Gus's fall"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["review_status"] == "confirmed"
    assert patch_response.json()["title"] == "Confirmed: Gus's fall"

    rebuild_response = client.post(f"/api/v1/patients/{SAMUEL_ID}/timeline/rebuild")
    assert rebuild_response.status_code == 200
    rebuilt = rebuild_response.json()["timeline_events"]
    rebuilt_target = next(e for e in rebuilt if e["event_id"] == target["event_id"])
    assert rebuilt_target["review_status"] == "confirmed"
    assert rebuilt_target["title"] == "Confirmed: Gus's fall"


def test_update_review_status_rejects_invalid_value():
    events = client.get(f"/api/v1/patients/{SAMUEL_ID}/timeline").json()["timeline_events"]
    event_id = events[0]["event_id"]
    response = client.patch(f"/api/v1/timeline-events/{event_id}", json={"review_status": "not-a-real-status"})
    assert response.status_code == 422


def test_update_unknown_event_returns_404():
    response = client.patch("/api/v1/timeline-events/does-not-exist", json={"review_status": "dismissed"})
    assert response.status_code == 404


def test_rebuild_unknown_patient_returns_404():
    response = client.post("/api/v1/patients/does-not-exist/timeline/rebuild")
    assert response.status_code == 404
