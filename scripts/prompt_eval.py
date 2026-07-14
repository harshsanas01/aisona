"""Prompt/model/retrieval-config regression gate (Feature 9: Prompt/Model
Versioning). Fingerprints every versioned prompt's exact text plus the
production retrieval-tuning constants, runs the existing retrieval and
grounded-answer evaluation layers, and compares both the fingerprint and
the resulting metrics against a checked-in baseline
(data/evaluation/prompt_eval_baseline.json).

Why this matters: prompt_version strings ("v1") are set by hand and easy to
forget to bump - this catches the case that actually matters, which is a
prompt, model, or retrieval-tuning change that silently degrades answer
quality. It reuses the same deterministic mock-mode evaluation the rest of
CI already runs (see docs/architecture/grounding.md) rather than an LLM
judge, so it is exact and reproducible run-over-run.

Usage:
    python scripts/prompt_eval.py                 # compare against baseline
    python scripts/prompt_eval.py --update-baseline  # record a new baseline

Exit code 0 on pass, 1 on regression or drift - suitable for CI gating.
"""
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "data" / "evaluation" / "prompt_eval_baseline.json"
RETRIEVAL_REPORT_PATH = ROOT / "artifacts" / "retrieval_evaluation.json"
GROUNDING_REPORT_PATH = ROOT / "artifacts" / "grounding_evaluation.json"

# Metrics where a lower value than baseline is a regression.
_HIGHER_IS_BETTER = (
    "hit_rate", "mean_recall", "mean_precision", "mean_reciprocal_rank",
    "unanswerable_accuracy", "grounding_pass_rate",
)


def _load_script_module(name: str, filename: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def current_fingerprint() -> dict:
    from carecall_api import config
    from carecall_domain import content_hash
    from carecall_llm.prompts import (
        BRIEF_PROSE_PROMPT,
        BRIEF_PROSE_PROMPT_VERSION,
        PROMPT_VERSION,
        SYSTEM_PROMPT,
        TIMELINE_EXTRACTION_PROMPT,
        TIMELINE_EXTRACTION_PROMPT_VERSION,
    )

    return {
        "system_prompt_version": PROMPT_VERSION,
        "system_prompt_hash": content_hash(SYSTEM_PROMPT),
        "timeline_extraction_prompt_version": TIMELINE_EXTRACTION_PROMPT_VERSION,
        "timeline_extraction_prompt_hash": content_hash(TIMELINE_EXTRACTION_PROMPT),
        "brief_prose_prompt_version": BRIEF_PROSE_PROMPT_VERSION,
        "brief_prose_prompt_hash": content_hash(BRIEF_PROSE_PROMPT),
        "lexical_weight": config.LEXICAL_WEIGHT,
        "semantic_weight": config.SEMANTIC_WEIGHT,
        "min_relevance_score": config.MIN_RELEVANCE_SCORE,
        "top_k": config.TOP_K,
    }


def current_metrics() -> dict:
    """Runs the existing retrieval + grounded-answer evaluation scripts
    in-process (reusing their real logic, not reimplementing it) and reads
    back the JSON reports they already write under artifacts/."""
    _load_script_module("_prompt_eval_retrieval_run", "evaluate_retrieval.py").main()
    _load_script_module("_prompt_eval_grounding_run", "evaluate_grounding.py").main()

    retrieval_report = json.loads(RETRIEVAL_REPORT_PATH.read_text())
    grounding_report = json.loads(GROUNDING_REPORT_PATH.read_text())
    grounding_total = grounding_report["total"]

    return {
        "hit_rate": retrieval_report["aggregate"]["hit_rate"],
        "mean_recall": retrieval_report["aggregate"]["mean_recall"],
        "mean_precision": retrieval_report["aggregate"]["mean_precision"],
        "mean_reciprocal_rank": retrieval_report["aggregate"]["mean_reciprocal_rank"],
        "unanswerable_accuracy": retrieval_report["aggregate"]["unanswerable_accuracy"],
        "grounding_pass_rate": (grounding_report["passed"] / grounding_total) if grounding_total else 1.0,
    }


def compare(baseline: dict, current: dict) -> list:
    """Returns a list of human-readable regression descriptions - empty if
    nothing regressed."""
    problems = []
    for metric in _HIGHER_IS_BETTER:
        base_value = baseline["metrics"].get(metric)
        current_value = current["metrics"].get(metric)
        if base_value is None or current_value is None:
            continue
        if current_value < base_value - 1e-9:
            problems.append(f"{metric} regressed: {base_value:.4f} -> {current_value:.4f}")
    return problems


def main() -> int:
    update_baseline = "--update-baseline" in sys.argv

    print("Computing current prompt/config fingerprint and running evaluation layers...")
    fingerprint = current_fingerprint()
    metrics = current_metrics()
    current = {"fingerprint": fingerprint, "metrics": metrics}

    print()
    print("Fingerprint:")
    for key, value in fingerprint.items():
        print(f"  {key}: {value}")
    print()
    print("Metrics:")
    for key, value in metrics.items():
        print(f"  {key}: {value:.4f}")

    if update_baseline or not BASELINE_PATH.exists():
        BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        BASELINE_PATH.write_text(json.dumps(current, indent=2) + "\n")
        print(f"\nBaseline written to {BASELINE_PATH}")
        return 0

    baseline = json.loads(BASELINE_PATH.read_text())
    fingerprint_changed = baseline["fingerprint"] != fingerprint
    problems = compare(baseline, current)

    print()
    if not fingerprint_changed and not problems:
        print("PASS: fingerprint and metrics both match the baseline exactly.")
        return 0

    if fingerprint_changed and not problems:
        print("PASS: prompt/model/retrieval config changed, but no metric regressed.")
        print("Run with --update-baseline to record this as the new baseline.")
        return 0

    if not fingerprint_changed and problems:
        print("FAIL: metrics changed with no fingerprint change - this points to nondeterminism")
        print("or a regression in code that isn't reflected in the fingerprint:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("FAIL: prompt/model/retrieval config changed and evaluation quality regressed:")
    for problem in problems:
        print(f"  - {problem}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
