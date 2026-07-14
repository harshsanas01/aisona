import uuid
from datetime import datetime, timezone
from typing import Optional

from carecall_domain import (
    TASK_CATEGORIES,
    TASK_PRIORITIES,
    CoordinatorTask,
    InvalidTaskFieldError,
    TaskActivity,
)

from ..ports.repositories import CoordinatorTaskRepository, TaskActivityRepository


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CreateTaskUseCase:
    """Coordinators create tasks manually from a citation or timeline
    event - this use case is also reused by SuggestTaskFromEventUseCase for
    system-suggested tasks, always with is_suggested explicit so a
    suggestion is never mistaken for a coordinator-confirmed action."""

    def __init__(self, task_repository: CoordinatorTaskRepository, activity_repository: TaskActivityRepository):
        self.task_repository = task_repository
        self.activity_repository = activity_repository

    def execute(
        self,
        *,
        title: str,
        description: str,
        patient_id: str,
        priority: str = "normal",
        category: str,
        created_by: str,
        source_event_id: Optional[str] = None,
        source_call_id: Optional[str] = None,
        source_turn_start: Optional[int] = None,
        source_turn_end: Optional[int] = None,
        assignee: Optional[str] = None,
        due_date: Optional[str] = None,
        is_suggested: bool = False,
        dedupe_key: Optional[str] = None,
    ) -> CoordinatorTask:
        if priority not in TASK_PRIORITIES:
            raise InvalidTaskFieldError(f"'{priority}' is not a valid priority; must be one of {TASK_PRIORITIES}")
        if category not in TASK_CATEGORIES:
            raise InvalidTaskFieldError(f"'{category}' is not a valid category; must be one of {TASK_CATEGORIES}")

        now = _utcnow_iso()
        task = CoordinatorTask(
            task_id=f"task-{uuid.uuid4().hex[:12]}",
            title=title,
            description=description,
            patient_id=patient_id,
            priority=priority,
            status="open",
            category=category,
            is_suggested=is_suggested,
            created_by=created_by,
            created_at=now,
            updated_at=now,
            source_event_id=source_event_id,
            source_call_id=source_call_id,
            source_turn_start=source_turn_start,
            source_turn_end=source_turn_end,
            assignee=assignee,
            due_date=due_date,
            dedupe_key=dedupe_key,
        )
        created = self.task_repository.create(task)
        self.activity_repository.add(TaskActivity(
            activity_id=f"act-{uuid.uuid4().hex[:12]}",
            task_id=created.task_id,
            action="suggested" if is_suggested else "created",
            actor=created_by,
            created_at=now,
            to_status="open",
        ))
        return created
