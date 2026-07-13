from dataclasses import dataclass


@dataclass(frozen=True)
class SafetyEvent:
    """An operational triage flag on a single transcript turn - NOT a
    medical diagnosis. category/severity are coarse and rule-based;
    matched_text and explanation are always included so a human reviewer
    can judge context (e.g. a third-party mention, a denial, a resolved
    issue) before acting on it."""

    category: str
    severity: str  # "low" | "medium" | "high"
    call_id: str
    turn_number: int
    matched_text: str
    explanation: str
    classifier_type: str  # "deterministic" | "llm"
