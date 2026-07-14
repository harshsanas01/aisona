from dataclasses import dataclass
from typing import Optional, Tuple

from .pattern_evidence_ref import PatternEvidenceRef

BRIEF_TYPES = ("daily", "weekly")

BRIEF_SECTIONS = (
    "high_attention",
    "follow_up_needed",
    "new_medication_changes",
    "recurring_concerns",
    "transportation_appointment_issues",
    "resolved_items",
    "task_status_summary",
)


@dataclass(frozen=True)
class BriefBullet:
    """One evidence-linked line item in a care brief. Every bullet carries
    the patient it's about and, wherever the underlying data has it, the
    exact timeline event/pattern/task it was selected from - a brief bullet
    is never freestanding prose."""

    bullet_id: str
    section: str  # one of BRIEF_SECTIONS
    patient_id: str
    patient_name: str
    summary: str
    related_timeline_event_ids: Tuple[str, ...]
    evidence: Tuple[PatternEvidenceRef, ...]
    related_pattern_id: Optional[str] = None
    related_task_id: Optional[str] = None


@dataclass(frozen=True)
class Brief:
    """A generated operational summary. Bullets are always selected from
    already-persisted structured data (timeline events, patterns, tasks) -
    see docs/architecture/audit-trail.md's sibling ADR "structured events
    before LLM summaries". An optional LLM stage may only rephrase a
    bullet's prose after selection; it can never add a bullet or evidence
    reference of its own."""

    brief_id: str
    brief_type: str  # one of BRIEF_TYPES
    start_date: str
    end_date: str
    include_resolved: bool
    bullets: Tuple[BriefBullet, ...]
    model_version: str
    prompt_version: str
    generated_at: str
    created_at: str
    updated_at: str
    patient_id: Optional[str] = None  # None means center-wide
