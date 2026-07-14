from dataclasses import dataclass
from typing import Optional

TIMELINE_EVENT_TYPES = (
    "medication_started",
    "medication_adherence_concern",
    "symptom_reported",
    "symptom_recurrence",
    "sleep_issue",
    "meal_concern",
    "transportation_issue",
    "appointment_request",
    "home_safety_concern",
    "assistive_device_update",
    "issue_resolved",
    "follow_up_promised",
    "other_safety_event",
)

TIMELINE_REVIEW_STATUSES = ("unreviewed", "confirmed", "corrected", "dismissed")


@dataclass(frozen=True)
class TimelineEvent:
    """A single longitudinal care event surfaced on a patient's timeline -
    an "observed transcript event", NOT a diagnosis. Every field that could
    support a coordinator's judgment call (source_call_id, the exact turn
    range, and the verbatim quote) is always present so the event can be
    traced back to the exact transcript moment it came from.

    review_status starts "unreviewed" and is only ever changed by a human
    coordinator via PATCH /api/v1/timeline-events/{event_id} - extraction
    (deterministic or LLM) never marks an event confirmed/corrected/dismissed
    itself.
    """

    event_id: str
    patient_id: str
    event_type: str  # one of TIMELINE_EVENT_TYPES
    title: str
    description: str
    observed_date: str
    source_call_id: str
    source_turn_start: int
    source_turn_end: int
    quote: str
    confidence: str  # "low" | "medium" | "high"
    extraction_method: str  # "deterministic" | "llm"
    review_status: str  # one of TIMELINE_REVIEW_STATUSES
    created_at: str
    updated_at: str
    dedupe_key: Optional[str] = None
