from fastapi.testclient import TestClient

from carecall_api.main import app

client = TestClient(app)


def _generate(**overrides):
    payload = {"type": "weekly", "start_date": "2026-05-01", "end_date": "2026-06-30", "include_resolved": True}
    payload.update(overrides)
    return client.post("/api/v1/briefs", json=payload)


def test_generate_center_wide_weekly_brief_has_evidence_linked_bullets():
    response = _generate()
    assert response.status_code == 201
    body = response.json()
    assert body["brief_type"] == "weekly"
    assert body["patient_id"] is None
    assert body["model_version"] == "deterministic"
    assert body["bullets"]

    bullet = body["bullets"][0]
    assert set(bullet.keys()) == {
        "bullet_id", "section", "patient_id", "patient_name", "summary",
        "related_timeline_event_ids", "related_pattern_id", "related_task_id", "evidence",
    }
    assert bullet["patient_name"]
    assert bullet["evidence"]
    assert bullet["evidence"][0]["call_id"]
    assert bullet["evidence"][0]["quote"]


def test_generate_patient_specific_brief_only_includes_that_patient():
    response = _generate(patient_id="P-1002")
    assert response.status_code == 201
    body = response.json()
    assert body["patient_id"] == "P-1002"
    assert all(b["patient_id"] == "P-1002" for b in body["bullets"])


def test_medication_started_before_symptom_bullet_never_uses_causal_wording():
    response = _generate(patient_id="P-1001")
    assert response.status_code == 201
    for bullet in response.json()["bullets"]:
        summary_lower = bullet["summary"].lower()
        assert "caused" not in summary_lower
        assert "diagnosis" not in summary_lower
        assert "confirmed adverse" not in summary_lower


def test_gus_fall_bullet_never_attributes_the_event_to_samuel():
    response = _generate(patient_id="P-1008")
    assert response.status_code == 201
    for bullet in response.json()["bullets"]:
        assert "Samuel" not in bullet["summary"]
        for ref in bullet["evidence"]:
            if ref["call_id"] == "call_021":
                assert "Gus" in ref["quote"]
                assert "Samuel" not in ref["quote"]


def test_generate_rejects_invalid_brief_type():
    response = _generate(type="monthly")
    assert response.status_code == 422


def test_generate_rejects_start_after_end():
    response = _generate(start_date="2026-06-30", end_date="2026-05-01")
    assert response.status_code == 422


def test_generate_for_unknown_patient_returns_404():
    response = _generate(patient_id="does-not-exist")
    assert response.status_code == 404


def test_get_brief_returns_the_generated_brief():
    created = _generate().json()
    response = client.get(f"/api/v1/briefs/{created['brief_id']}")
    assert response.status_code == 200
    assert response.json()["brief_id"] == created["brief_id"]


def test_get_unknown_brief_returns_404():
    response = client.get("/api/v1/briefs/does-not-exist")
    assert response.status_code == 404


def test_list_briefs_includes_generated_brief():
    created = _generate().json()
    response = client.get("/api/v1/briefs")
    assert response.status_code == 200
    ids = [b["brief_id"] for b in response.json()["briefs"]]
    assert created["brief_id"] in ids


def test_list_briefs_filters_by_type():
    daily = _generate(type="daily", start_date="2026-06-01", end_date="2026-06-01").json()
    response = client.get("/api/v1/briefs", params={"type": "daily"})
    ids = [b["brief_id"] for b in response.json()["briefs"]]
    assert daily["brief_id"] in ids
    assert all(b["brief_type"] == "daily" for b in response.json()["briefs"])


def test_regenerate_keeps_the_same_brief_id():
    created = _generate().json()
    response = client.post(f"/api/v1/briefs/{created['brief_id']}/regenerate")
    assert response.status_code == 200
    assert response.json()["brief_id"] == created["brief_id"]


def test_regenerate_unknown_brief_returns_404():
    response = client.post("/api/v1/briefs/does-not-exist/regenerate")
    assert response.status_code == 404
