"""Ingests data/raw/carecall_transcripts.json into a running CareCall API
instance via POST /api/calls/batch, in bounded batches (the endpoint caps
a single batch at 20 calls). Useful for seeding a fresh PostgreSQL database
through the real ingestion path (rather than only via the lifespan
first-boot bootstrap) or for demonstrating idempotent re-seeding - already-
ingested calls come back with status "duplicate", not an error.

Usage: python scripts/ingest_fixture_data.py [base_url]
"""
import json
import sys
import urllib.request
from pathlib import Path

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
FIXTURE_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "carecall_transcripts.json"
BATCH_SIZE = 20


def post_batch(calls: list) -> list:
    req = urllib.request.Request(
        f"{BASE_URL}/api/calls/batch",
        data=json.dumps({"calls": calls}).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def main() -> int:
    calls = json.loads(FIXTURE_PATH.read_text())["calls"]
    print(f"Seeding {len(calls)} calls from {FIXTURE_PATH} into {BASE_URL} ...")

    created = duplicate = errored = 0
    for start in range(0, len(calls), BATCH_SIZE):
        batch = calls[start:start + BATCH_SIZE]
        results = post_batch(batch)
        for result in results:
            print(f"  {result['call_id']}: {result['status']}")
            if result["status"] == "created":
                created += 1
            elif result["status"] == "duplicate":
                duplicate += 1
            else:
                errored += 1

    print(f"\nDone: {created} created, {duplicate} already present, {errored} errored")
    return 1 if errored else 0


if __name__ == "__main__":
    raise SystemExit(main())
