from dataclasses import dataclass, field
from typing import Tuple

from .pattern_evidence_ref import PatternEvidenceRef

PATTERN_TYPES = (
    "first_occurrence",
    "repeated_occurrence",
    "increasing_frequency",
    "worsening_wording",
    "issue_resolved",
    "recurrence_after_resolution",
    "medication_started_before_symptom",
    "repeated_transportation_issue",
    "repeated_missed_medication",
    "repeated_sleep_issue",
    "repeated_meal_concern",
)

PATTERN_STATUSES = ("active", "resolved", "uncertain")
PATTERN_SEVERITIES = ("informational", "attention", "high_attention")
PATTERN_REVIEW_STATUSES = ("unreviewed", "confirmed", "corrected", "dismissed")


@dataclass(frozen=True)
class PatientPattern:
    """A longitudinal pattern detected across a patient's timeline events -
    an evidence-based observation, never a causal or clinical conclusion.
    Every field needed to trace the pattern back to real transcript
    evidence (related_timeline_event_ids, related_call_ids, evidence) is
    always present."""

    pattern_id: str
    patient_id: str
    pattern_type: str  # one of PATTERN_TYPES
    title: str
    summary: str
    status: str  # one of PATTERN_STATUSES
    severity: str  # one of PATTERN_SEVERITIES
    first_observed_date: str
    latest_observed_date: str
    related_timeline_event_ids: Tuple[str, ...]
    related_call_ids: Tuple[str, ...]
    evidence: Tuple[PatternEvidenceRef, ...]
    detector_version: str
    reviewed_status: str  # one of PATTERN_REVIEW_STATUSES
    created_at: str
    updated_at: str
    dedupe_key: str = field(default="")
