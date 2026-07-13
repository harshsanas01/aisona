"""Grounded-answer evaluation layer, run over both the original 8-question
set and the adversarial question set:

- every citation references a real call and an in-bounds turn range
- the citation quote is actually derived from that call's real turns
- unanswerable responses never carry citations
- answerable/unanswerable expectations are met, including the
  forbidden_source_calls check (a third-party event must not be
  misattributed to the wrong person - see data/evaluation/adversarial_questions.json)

Deliberately not an LLM-judge: every check here is a structural/lexical
fact check against the corpus, not a subjective quality judgment. Writes a
terminal report plus a JSON report under artifacts/.
"""
import json
from pathlib import Path
from typing import List

from carecall_api.lifespan import build_container

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_QUESTIONS_PATH = ROOT / "data" / "evaluation" / "carecall_questions.json"
ADVERSARIAL_QUESTIONS_PATH = ROOT / "data" / "evaluation" / "adversarial_questions.json"
REPORT_PATH = ROOT / "artifacts" / "grounding_evaluation.json"


def _validate_citation(citation, call_repository) -> List[str]:
    problems = []
    call = call_repository.get_call(citation.call_id)
    if call is None:
        problems.append(f"references unknown call_id {citation.call_id}")
        return problems

    if not (1 <= citation.turn_start <= citation.turn_end <= len(call.turns)):
        problems.append(
            f"turn range {citation.turn_start}-{citation.turn_end} out of bounds "
            f"for {citation.call_id} ({len(call.turns)} turns)"
        )
        return problems

    actual_text = " | ".join(
        f"{turn.speaker}: {turn.text}" for turn in call.turns[citation.turn_start - 1:citation.turn_end]
    )
    if citation.quote and citation.quote not in actual_text:
        problems.append(f"quote not found verbatim in {citation.call_id} turns {citation.turn_start}-{citation.turn_end}")

    return problems


def _evaluate_question(container, question: dict, label: str) -> dict:
    response = container.ask_question.execute(question["question"])
    problems: List[str] = []

    if not response.answerable and response.citations:
        problems.append("unanswerable response carries citations")

    for citation in response.citations:
        problems.extend(_validate_citation(citation, container.call_repository))

    expected_answerable = question.get("expected_answerable")
    if expected_answerable is not None and response.answerable != expected_answerable:
        problems.append(f"expected answerable={expected_answerable}, got {response.answerable}")

    cited = {c.call_id for c in response.citations}

    expected_source_calls = question.get("expected_source_calls")
    if expected_source_calls:
        missing = set(expected_source_calls) - cited
        if missing:
            problems.append(f"missing expected source calls: {sorted(missing)}")

    forbidden_source_calls = question.get("forbidden_source_calls")
    if forbidden_source_calls:
        present = set(forbidden_source_calls) & cited
        if present:
            problems.append(f"forbidden source calls present: {sorted(present)}")

    status = "PASS" if not problems else "FAIL"
    return {
        "set": label,
        "id": question["id"],
        "question": question["question"],
        "status": status,
        "problems": problems,
    }


def main() -> int:
    container = build_container()
    per_question = []

    for path, label in [(ORIGINAL_QUESTIONS_PATH, "original"), (ADVERSARIAL_QUESTIONS_PATH, "adversarial")]:
        questions = json.loads(path.read_text())["questions"]
        for question in questions:
            result = _evaluate_question(container, question, label)
            status_line = f"[{result['set']}] {result['id']} {result['status']}"
            if result["problems"]:
                status_line += " - " + "; ".join(result["problems"])
            print(status_line)
            per_question.append(result)

    total = len(per_question)
    passed = sum(1 for q in per_question if q["status"] == "PASS")
    print()
    print(f"Grounded-answer evaluation: {passed}/{total} passed")

    REPORT_PATH.parent.mkdir(exist_ok=True)
    REPORT_PATH.write_text(json.dumps({"per_question": per_question, "passed": passed, "total": total}, indent=2))
    print(f"JSON report written to {REPORT_PATH}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
