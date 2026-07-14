from fastapi.testclient import TestClient

from carecall_api.main import app

client = TestClient(app)

MARGARET_ID = "P-1001"  # has a repeated symptom pattern and a medication-before-symptom pattern
SAMUEL_ID = "P-1008"  # call_021 reports Gus's (his neighbor's) fall


def test_get_patient_patterns_shape():
    response = client.get(f"/api/v1/patients/{MARGARET_ID}/patterns")
    assert response.status_code == 200
    body = response.json()
    patterns = body["patterns"]
    assert patterns
    assert set(patterns[0].keys()) == {
        "pattern_id", "patient_id", "pattern_type", "title", "summary", "status", "severity",
        "first_observed_date", "latest_observed_date", "related_timeline_event_ids", "related_call_ids",
        "evidence", "detector_version", "reviewed_status", "created_at", "updated_at",
    }


def test_medication_started_before_symptom_pattern_uses_non_causal_wording():
    response = client.get(f"/api/v1/patients/{MARGARET_ID}/patterns")
    patterns = response.json()["patterns"]
    med_patterns = [p for p in patterns if p["pattern_type"] == "medication_started_before_symptom"]
    assert len(med_patterns) == 1
    summary = med_patterns[0]["summary"].lower()
    assert "temporal observation only" in summary
    assert "caused" not in summary
    assert med_patterns[0]["status"] == "uncertain"


def test_gus_fall_pattern_never_attributes_the_event_to_samuel():
    response = client.get(f"/api/v1/patients/{SAMUEL_ID}/patterns")
    assert response.status_code == 200
    patterns = response.json()["patterns"]
    assert patterns
    for pattern in patterns:
        assert "Samuel" not in pattern["summary"]
        for ref in pattern["evidence"]:
            if ref["call_id"] == "call_021":
                assert "Gus" in ref["quote"]
                assert "Samuel" not in ref["quote"]


def test_get_patterns_for_unknown_patient_returns_404():
    response = client.get("/api/v1/patients/does-not-exist/patterns")
    assert response.status_code == 404


def test_update_reviewed_status_then_rebuild_preserves_it():
    patterns_before = client.get(f"/api/v1/patients/{MARGARET_ID}/patterns").json()["patterns"]
    target = next(p for p in patterns_before if p["pattern_type"] == "repeated_occurrence")

    patch_response = client.patch(
        f"/api/v1/patterns/{target['pattern_id']}", json={"reviewed_status": "confirmed"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["reviewed_status"] == "confirmed"

    rebuild_response = client.post(f"/api/v1/patients/{MARGARET_ID}/patterns/rebuild")
    assert rebuild_response.status_code == 200
    rebuilt = rebuild_response.json()["patterns"]
    rebuilt_target = next(p for p in rebuilt if p["pattern_id"] == target["pattern_id"])
    assert rebuilt_target["reviewed_status"] == "confirmed"


def test_update_reviewed_status_rejects_invalid_value():
    patterns = client.get(f"/api/v1/patients/{MARGARET_ID}/patterns").json()["patterns"]
    pattern_id = patterns[0]["pattern_id"]
    response = client.patch(f"/api/v1/patterns/{pattern_id}", json={"reviewed_status": "not-a-real-status"})
    assert response.status_code == 422


def test_update_unknown_pattern_returns_404():
    response = client.patch("/api/v1/patterns/does-not-exist", json={"reviewed_status": "dismissed"})
    assert response.status_code == 404


def test_rebuild_unknown_patient_returns_404():
    response = client.post("/api/v1/patients/does-not-exist/patterns/rebuild")
    assert response.status_code == 404


def test_patient_summary_includes_pattern_counts():
    response = client.get(f"/api/v1/patients/{MARGARET_ID}")
    assert response.status_code == 200
    body = response.json()
    assert "pattern_count" in body
    assert "attention_pattern_count" in body
    assert body["pattern_count"] >= 1
