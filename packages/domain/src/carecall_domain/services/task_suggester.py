from dataclasses import dataclass
from typing import Optional

from ..entities.timeline_event import TimelineEvent

# issue_resolved never generates a suggestion - the concern it describes is
# already reported resolved, so no fresh outreach is implied.
_CATEGORY_FOR_EVENT_TYPE = {
    "medication_started": "medication_review",
    "medication_adherence_concern": "medication_review",
    "symptom_reported": "nurse_follow_up",
    "symptom_recurrence": "nurse_follow_up",
    "sleep_issue": "nurse_follow_up",
    "meal_concern": "meal_support",
    "transportation_issue": "transportation",
    "appointment_request": "appointment",
    "home_safety_concern": "home_safety",
    "assistive_device_update": "general_outreach",
    "follow_up_promised": "nurse_follow_up",
    "other_safety_event": "general_outreach",
}

_PRIORITY_FOR_EVENT_TYPE = {
    "medication_adherence_concern": "high",
    "home_safety_concern": "high",
    "symptom_recurrence": "high",
}


@dataclass(frozen=True)
class SuggestedTaskDraft:
    """A candidate task derived from a timeline event - never persisted or
    assigned by this function itself. The caller (a use case) always
    persists it with is_suggested=True and status="open", leaving every
    other coordinator decision (assignee, due date, status changes) to a
    human."""

    title: str
    description: str
    category: str
    priority: str


def suggest_task_draft(event: TimelineEvent) -> Optional[SuggestedTaskDraft]:
    category = _CATEGORY_FOR_EVENT_TYPE.get(event.event_type)
    if category is None:
        return None
    priority = _PRIORITY_FOR_EVENT_TYPE.get(event.event_type, "normal")
    return SuggestedTaskDraft(
        title=f"Follow up: {event.title}",
        description=(
            f"Coordinator follow-up suggested based on an observed transcript event "
            f"(call {event.source_call_id}, {event.observed_date}). Review the linked evidence "
            "before contacting the patient. This is a suggestion, not a clinical instruction."
        ),
        category=category,
        priority=priority,
    )
