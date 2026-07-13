from fastapi.testclient import TestClient

from carecall_api.main import app

client = TestClient(app)

NEW_CALL = {
    "call_id": "call_test_ingest_001",
    "date": "2026-07-01",
    "patient": {"id": "P-9999", "name": "Ingestion Testerson", "age": 81},
    "duration_seconds": 60,
    "turns": [
        {"speaker": "assistant", "text": "Hello, how are you feeling today?"},
        {"speaker": "participant", "text": "I've had a persistent zolbotanium headache since Tuesday."},
    ],
}


def test_ingest_new_call_returns_201_with_chunk_count():
    response = client.post("/api/calls", json=NEW_CALL)
    assert response.status_code == 201
    body = response.json()
    assert body["call_id"] == "call_test_ingest_001"
    assert body["status"] == "created"
    assert body["chunk_count"] >= 1


def test_ingested_call_is_immediately_retrievable_by_id():
    response = client.get("/api/calls/call_test_ingest_001")
    assert response.status_code == 200
    body = response.json()
    assert body["patient"]["name"] == "Ingestion Testerson"


def test_ingested_call_is_immediately_searchable():
    # "zolbotanium" is a made-up term that only appears in the freshly
    # ingested call, so a hit here proves the retrieval index was
    # refreshed rather than serving a stale startup snapshot.
    response = client.post("/api/ask", json={"question": "Who mentioned a zolbotanium headache?"})
    assert response.status_code == 200
    body = response.json()
    assert body["answerable"] is True
    assert any(c["call_id"] == "call_test_ingest_001" for c in body["citations"])


def test_duplicate_ingestion_is_rejected_with_409():
    response = client.post("/api/calls", json=NEW_CALL)
    assert response.status_code == 409


def test_batch_ingest_bounded_size_is_rejected():
    oversized = {"calls": [
        {**NEW_CALL, "call_id": f"call_batch_overflow_{i}"} for i in range(25)
    ]}
    response = client.post("/api/calls/batch", json=oversized)
    assert response.status_code == 422


def test_batch_ingest_reports_per_call_status_including_duplicates():
    payload = {"calls": [
        {**NEW_CALL, "call_id": "call_test_batch_001"},
        NEW_CALL,  # already ingested above -> should report duplicate, not abort the batch
    ]}
    response = client.post("/api/calls/batch", json=payload)
    assert response.status_code == 200
    results = {item["call_id"]: item["status"] for item in response.json()}
    assert results["call_test_batch_001"] == "created"
    assert results["call_test_ingest_001"] == "duplicate"


def test_ingest_rejects_call_with_no_turns():
    invalid = {**NEW_CALL, "call_id": "call_invalid_no_turns", "turns": []}
    response = client.post("/api/calls", json=invalid)
    assert response.status_code == 422
