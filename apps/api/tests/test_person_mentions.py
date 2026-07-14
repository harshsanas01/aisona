from fastapi.testclient import TestClient

from carecall_api.main import app

client = TestClient(app)

SAMUEL_ID = "P-1008"  # Samuel Rivera - call_021 reports Gus's (his neighbor's) fall


def test_get_person_mentions_shape_and_gus_never_typed_as_family_or_participant():
    response = client.get(f"/api/v1/patients/{SAMUEL_ID}/people")
    assert response.status_code == 200
    body = response.json()
    mentions = body["person_mentions"]
    assert mentions
    assert set(mentions[0].keys()) == {
        "mention_id", "patient_id", "source_call_id", "source_turn", "quote",
        "role_label", "relationship_type", "mentioned_name", "confidence",
        "extraction_method", "review_status", "created_at", "updated_at",
    }

    gus_mentions = [m for m in mentions if m["mentioned_name"] == "Gus"]
    assert gus_mentions
    for mention in gus_mentions:
        assert mention["relationship_type"] == "neighbor"
        assert mention["patient_id"] == SAMUEL_ID

    # No mention on Samuel's own record ever carries relationship_type
    # "family" or "participant" pointed at Gus's third-party relative
    # ("his son") - that ambiguous reference must stay "unknown".
    son_mentions = [m for m in mentions if m["role_label"] == "son"]
    assert son_mentions
    for mention in son_mentions:
        assert mention["relationship_type"] == "unknown"
        assert mention["mentioned_name"] is None


def test_get_person_mentions_can_filter_by_relationship_type():
    response = client.get(f"/api/v1/patients/{SAMUEL_ID}/people", params={"relationship_type": "neighbor"})
    assert response.status_code == 200
    mentions = response.json()["person_mentions"]
    assert mentions
    assert all(m["relationship_type"] == "neighbor" for m in mentions)


def test_get_person_mentions_for_unknown_patient_returns_404():
    response = client.get("/api/v1/patients/does-not-exist/people")
    assert response.status_code == 404


def test_rebuild_person_mentions_for_unknown_patient_returns_404():
    response = client.post("/api/v1/patients/does-not-exist/people/rebuild")
    assert response.status_code == 404


def test_rebuild_person_mentions_returns_the_same_mentions():
    before = client.get(f"/api/v1/patients/{SAMUEL_ID}/people").json()["person_mentions"]
    rebuilt = client.post(f"/api/v1/patients/{SAMUEL_ID}/people/rebuild").json()["person_mentions"]
    assert {m["mention_id"] for m in before} == {m["mention_id"] for m in rebuilt}


def test_update_review_status_then_rebuild_preserves_it():
    mentions_before = client.get(f"/api/v1/patients/{SAMUEL_ID}/people").json()["person_mentions"]
    target = next(m for m in mentions_before if m["mentioned_name"] == "Gus")

    patch_response = client.patch(
        f"/api/v1/person-mentions/{target['mention_id']}", json={"review_status": "confirmed"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["review_status"] == "confirmed"

    rebuild_response = client.post(f"/api/v1/patients/{SAMUEL_ID}/people/rebuild")
    rebuilt = rebuild_response.json()["person_mentions"]
    rebuilt_target = next(m for m in rebuilt if m["mention_id"] == target["mention_id"])
    assert rebuilt_target["review_status"] == "confirmed"


def test_update_review_status_rejects_invalid_value():
    mentions = client.get(f"/api/v1/patients/{SAMUEL_ID}/people").json()["person_mentions"]
    mention_id = mentions[0]["mention_id"]
    response = client.patch(f"/api/v1/person-mentions/{mention_id}", json={"review_status": "not-a-real-status"})
    assert response.status_code == 422


def test_update_unknown_mention_returns_404():
    response = client.patch("/api/v1/person-mentions/does-not-exist", json={"review_status": "dismissed"})
    assert response.status_code == 404


def test_coordinator_can_correct_an_unknown_mention_to_participant():
    """The only path by which relationship_type "participant" can ever be
    set - a human coordinator recognizing the mentioned person is also a
    CareCall program participant."""
    mentions = client.get(f"/api/v1/patients/{SAMUEL_ID}/people").json()["person_mentions"]
    unknown_mention = next(m for m in mentions if m["relationship_type"] == "unknown")

    response = client.patch(
        f"/api/v1/person-mentions/{unknown_mention['mention_id']}",
        json={
            "review_status": "corrected",
            "corrected_relationship_type": "participant",
            "corrected_name": "Frank Delgado",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["relationship_type"] == "participant"
    assert body["mentioned_name"] == "Frank Delgado"
    assert body["review_status"] == "corrected"


def test_feedback_on_person_mention_syncs_review_status():
    mentions = client.get(f"/api/v1/patients/{SAMUEL_ID}/people").json()["person_mentions"]
    target = next(m for m in mentions if m["relationship_type"] == "staff")

    response = client.post(
        "/api/v1/feedback",
        json={
            "target_type": "person_mention",
            "target_id": target["mention_id"],
            "category": "dismiss",
            "actor": "coordinator_amy",
        },
    )
    assert response.status_code == 200

    updated = client.get(f"/api/v1/patients/{SAMUEL_ID}/people").json()["person_mentions"]
    updated_target = next(m for m in updated if m["mention_id"] == target["mention_id"])
    assert updated_target["review_status"] == "dismissed"


def test_feedback_rejects_answer_only_category_for_person_mention():
    mentions = client.get(f"/api/v1/patients/{SAMUEL_ID}/people").json()["person_mentions"]
    target = mentions[0]
    response = client.post(
        "/api/v1/feedback",
        json={
            "target_type": "person_mention",
            "target_id": target["mention_id"],
            "category": "unsupported_claim",
            "actor": "amy",
        },
    )
    assert response.status_code == 422
