from dataclasses import dataclass
from typing import Optional

TASK_PRIORITIES = ("low", "normal", "high", "urgent")
TASK_STATUSES = ("open", "in_progress", "blocked", "completed", "dismissed")
TASK_CATEGORIES = (
    "nurse_follow_up",
    "transportation",
    "medication_review",
    "appointment",
    "meal_support",
    "home_safety",
    "general_outreach",
)

# Which status transitions are allowed - status changes always go through
# UpdateTaskStatusUseCase, which rejects anything not listed here rather
# than silently allowing an invalid workflow state (e.g. "dismissed"
# jumping straight to "completed" without being reopened first).
TASK_STATUS_TRANSITIONS = {
    "open": ("in_progress", "blocked", "completed", "dismissed"),
    "in_progress": ("open", "blocked", "completed", "dismissed"),
    "blocked": ("open", "in_progress", "dismissed"),
    "completed": ("open",),
    "dismissed": ("open",),
}


@dataclass(frozen=True)
class CoordinatorTask:
    """A follow-up task for a care coordinator. May be created manually from
    a citation or timeline event, or suggested by the system - is_suggested
    is always explicit so a suggestion is never mistaken for a coordinator
    -confirmed action, and the system never auto-assigns or auto-completes a
    task itself."""

    task_id: str
    title: str
    description: str
    patient_id: str
    priority: str  # one of TASK_PRIORITIES
    status: str  # one of TASK_STATUSES
    category: str  # one of TASK_CATEGORIES
    is_suggested: bool
    created_by: str
    created_at: str
    updated_at: str
    source_event_id: Optional[str] = None
    source_call_id: Optional[str] = None
    source_turn_start: Optional[int] = None
    source_turn_end: Optional[int] = None
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    completed_at: Optional[str] = None
    dedupe_key: Optional[str] = None


@dataclass(frozen=True)
class TaskActivity:
    """Append-only activity history for a task - every creation and status
    transition is recorded so a coordinator can see who did what, when."""

    activity_id: str
    task_id: str
    action: str
    actor: str
    created_at: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    note: Optional[str] = None
