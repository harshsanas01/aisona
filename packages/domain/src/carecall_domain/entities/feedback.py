from dataclasses import dataclass
from typing import Optional

FEEDBACK_TARGET_TYPES = ("answer", "timeline_event", "pattern", "person_mention")

# Categories for feedback on a grounded answer (target_type="answer").
ANSWER_FEEDBACK_CATEGORIES = (
    "correct",
    "partially_correct",
    "incorrect",
    "missing_source",
    "wrong_source",
    "irrelevant_answer",
    "unsupported_claim",
)

# Categories for feedback on a timeline event, pattern, or person mention
# (target_type in "timeline_event"/"pattern"/"person_mention").
# "merge_duplicate" is feedback-only for now - there is no automated
# duplicate-merge workflow yet, so it is recorded for a human to act on
# manually, not applied automatically.
REVIEW_FEEDBACK_CATEGORIES = ("confirm", "correct", "dismiss", "merge_duplicate")

FEEDBACK_CATEGORIES_BY_TARGET_TYPE = {
    "answer": ANSWER_FEEDBACK_CATEGORIES,
    "timeline_event": REVIEW_FEEDBACK_CATEGORIES,
    "pattern": REVIEW_FEEDBACK_CATEGORIES,
    "person_mention": REVIEW_FEEDBACK_CATEGORIES,
}


@dataclass(frozen=True)
class Feedback:
    """One piece of human feedback on either a grounded answer or a
    reviewable item (timeline event / pattern). This is an append-only
    history of feedback *events* - distinct from a timeline event's or
    pattern's own review_status/reviewed_status field, which reflects only
    its current state. Feedback is used in evaluation exports but never
    automatically changes production behavior (see ADR: human-reviewed task
    suggestions for the same principle applied elsewhere)."""

    feedback_id: str
    target_type: str  # one of FEEDBACK_TARGET_TYPES
    target_id: str
    category: str  # must be in FEEDBACK_CATEGORIES_BY_TARGET_TYPE[target_type]
    actor: str
    created_at: str
    comment: Optional[str] = None
    corrected_value: Optional[str] = None
    prompt_version: Optional[str] = None
    retrieval_version: Optional[str] = None
    model_version: Optional[str] = None
