"""Retrieval evaluation layer: recall, precision, mean reciprocal rank, and
unanswerable accuracy against data/evaluation/carecall_questions.json.

Complements the original hit-rate-only scripts/evaluate.py with the finer-
grained metrics called for in the optional evaluation extension. Writes a
terminal report plus a JSON report under artifacts/.
"""
import json
from pathlib import Path

from carecall_api.lifespan import build_container
from carecall_retrieval import RetrievalEvaluationReport, evaluate_retrieval_question

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_PATH = ROOT / "data" / "evaluation" / "carecall_questions.json"
REPORT_PATH = ROOT / "artifacts" / "retrieval_evaluation.json"


def main() -> int:
    container = build_container()
    questions = json.loads(QUESTIONS_PATH.read_text())["questions"]

    results = []
    for q in questions:
        response = container.ask_question.execute(q["question"])
        cited = [c.call_id for c in response.citations]
        results.append(evaluate_retrieval_question(q["id"], q["expected_source_calls"], cited, response.answerable))

    report = RetrievalEvaluationReport(results)

    for r in results:
        status = "PASS" if r.hit else "FAIL"
        print(
            f"{r.question_id} {status} "
            f"recall={r.recall:.2f} precision={r.precision:.2f} rr={r.reciprocal_rank:.2f} "
            f"expected={list(r.expected)} cited={list(r.cited)}"
        )

    print()
    print(f"Hit rate:               {report.hit_rate:.0%}")
    print(f"Mean recall:            {report.mean_recall:.2f}")
    print(f"Mean precision:         {report.mean_precision:.2f}")
    print(f"Mean reciprocal rank:   {report.mean_reciprocal_rank:.2f}")
    print(f"Unanswerable accuracy:  {report.unanswerable_accuracy:.0%}")

    REPORT_PATH.parent.mkdir(exist_ok=True)
    REPORT_PATH.write_text(json.dumps({
        "per_question": [
            {
                "question_id": r.question_id,
                "expected": list(r.expected),
                "cited": list(r.cited),
                "answerable": r.answerable,
                "recall": r.recall,
                "precision": r.precision,
                "reciprocal_rank": r.reciprocal_rank,
                "hit": r.hit,
            }
            for r in results
        ],
        "aggregate": {
            "hit_rate": report.hit_rate,
            "mean_recall": report.mean_recall,
            "mean_precision": report.mean_precision,
            "mean_reciprocal_rank": report.mean_reciprocal_rank,
            "unanswerable_accuracy": report.unanswerable_accuracy,
        },
    }, indent=2))
    print(f"\nJSON report written to {REPORT_PATH}")

    return 0 if report.hit_rate == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
