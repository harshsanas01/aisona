"""End-to-end smoke test against a running CareCall API instance (memory or
postgres mode, mock or openai answer mode - it only talks HTTP). Exercises
the checklist from the migration/verification plan: ask a supported
question and inspect citations, open the cited transcript, apply a filter,
stream an answer, ingest a new transcript and immediately query it, and
confirm an unsupported question returns no citations.

Usage: python scripts/smoke_test.py [base_url]  (default http://localhost:8000)
"""
import json
import sys
import urllib.error
import urllib.request

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

_failures = []


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"{status} {label}" + (f" - {detail}" if detail and not condition else ""))
    if not condition:
        _failures.append(label)


def request(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def stream_request(body: dict) -> str:
    req = urllib.request.Request(
        f"{BASE_URL}/api/ask/stream", data=json.dumps(body).encode(),
        method="POST", headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode()


def main() -> int:
    status, health = request("GET", "/api/health")
    check("health endpoint responds", status == 200 and health.get("status") == "ok")

    # Supported question -> citations -> open transcript
    status, ask = request("POST", "/api/ask", {"question": "What new medication did Margaret Chen start?"})
    check("supported question is answerable", status == 200 and ask.get("answerable") is True)
    citations = ask.get("citations", [])
    check("supported question has citations", bool(citations))
    if citations:
        citation = citations[0]
        status, transcript = request("GET", f"/api/calls/{citation['call_id']}")
        check("cited transcript opens", status == 200 and transcript.get("call_id") == citation["call_id"])
        turn_numbers = {t["turn_number"] for t in transcript.get("turns", [])}
        check(
            "cited turn range exists in transcript",
            citation["turn_start"] in turn_numbers and citation["turn_end"] in turn_numbers,
        )

    # Patient filter
    status, patients = request("GET", "/api/patients")
    check("patients endpoint responds", status == 200 and patients.get("patients"))
    if patients.get("patients"):
        first_patient_id = patients["patients"][0]["id"]
        status, filtered = request("POST", "/api/ask", {
            "question": "How are they doing?", "patient_id": first_patient_id,
        })
        check("filtered question responds", status == 200)

    # Streaming
    stream_body = stream_request({"question": "Who has been having trouble sleeping?"})
    check("stream contains retrieval_started", "event: retrieval_started" in stream_body)
    check("stream contains citations event", "event: citations" in stream_body)
    check("stream contains completed event", "event: completed" in stream_body)

    # Ingest a new transcript, then query it
    new_call = {
        "call_id": "call_smoke_test_001",
        "date": "2026-07-13",
        "patient": {"id": "P-SMOKE", "name": "Smoke Tester", "age": 70},
        "duration_seconds": 30,
        "turns": [
            {"speaker": "assistant", "text": "How are you?"},
            {"speaker": "participant", "text": "I have a smoketestium condition today."},
        ],
    }
    status, ingest_result = request("POST", "/api/calls", new_call)
    check("ingestion returns 201", status == 201, f"got {status}: {ingest_result}")

    status, ask_new = request("POST", "/api/ask", {"question": "Who has a smoketestium condition?"})
    cited_new = {c["call_id"] for c in ask_new.get("citations", [])}
    check(
        "newly ingested call is immediately searchable",
        status == 200 and "call_smoke_test_001" in cited_new,
        f"cited={cited_new}",
    )

    # Unsupported question
    status, unsupported = request("POST", "/api/ask", {"question": "What is today's weather in LA?"})
    check(
        "unsupported question returns no citations",
        status == 200 and unsupported.get("answerable") is False and unsupported.get("citations") == [],
    )

    print()
    if _failures:
        print(f"SMOKE TEST FAILED: {len(_failures)} check(s) failed: {_failures}")
        return 1
    print("SMOKE TEST PASSED: all checks green")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
