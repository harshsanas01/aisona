import uuid
from dataclasses import replace
from datetime import datetime, timezone
from typing import Optional

from carecall_domain import (
    TASK_CATEGORIES,
    TASK_PRIORITIES,
    TASK_STATUS_TRANSITIONS,
    CoordinatorTask,
    InvalidTaskFieldError,
    InvalidTaskStatusTransitionError,
    TaskActivity,
)

from ..ports.repositories import CoordinatorTaskRepository, TaskActivityRepository


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class UpdateTaskUseCase:
    """Every task field edit and status transition goes through here so
    status changes are always validated against TASK_STATUS_TRANSITIONS and
    always recorded in the task's activity history - there is no other way
    to change a task's status. Completing/reopening a task
    (POST .../complete, POST .../reopen) are just this use case called with
    status="completed"/"open"."""

    def __init__(self, task_repository: CoordinatorTaskRepository, activity_repository: TaskActivityRepository):
        self.task_repository = task_repository
        self.activity_repository = activity_repository

    def execute(
        self,
        task_id: str,
        *,
        actor: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        assignee: Optional[str] = None,
        due_date: Optional[str] = None,
        status: Optional[str] = None,
        note: Optional[str] = None,
    ) -> Optional[CoordinatorTask]:
        task = self.task_repository.get(task_id)
        if task is None:
            return None

        if priority is not None and priority not in TASK_PRIORITIES:
            raise InvalidTaskFieldError(f"'{priority}' is not a valid priority; must be one of {TASK_PRIORITIES}")
        if category is not None and category not in TASK_CATEGORIES:
            raise InvalidTaskFieldError(f"'{category}' is not a valid category; must be one of {TASK_CATEGORIES}")

        status_changed = status is not None and status != task.status
        if status_changed:
            allowed = TASK_STATUS_TRANSITIONS.get(task.status, ())
            if status not in allowed:
                raise InvalidTaskStatusTransitionError(
                    f"Cannot transition task from '{task.status}' to '{status}'; allowed: {allowed}"
                )

        new_status = status if status_changed else task.status
        completed_at = task.completed_at
        if new_status == "completed" and task.status != "completed":
            completed_at = _utcnow_iso()
        elif new_status != "completed":
            completed_at = None

        updated = replace(
            task,
            title=title if title is not None else task.title,
            description=description if description is not None else task.description,
            priority=priority if priority is not None else task.priority,
            category=category if category is not None else task.category,
            assignee=assignee if assignee is not None else task.assignee,
            due_date=due_date if due_date is not None else task.due_date,
            status=new_status,
            completed_at=completed_at,
            updated_at=_utcnow_iso(),
        )
        saved = self.task_repository.update(updated)

        self.activity_repository.add(TaskActivity(
            activity_id=f"act-{uuid.uuid4().hex[:12]}",
            task_id=task_id,
            action="status_changed" if status_changed else "updated",
            actor=actor,
            created_at=_utcnow_iso(),
            from_status=task.status if status_changed else None,
            to_status=new_status if status_changed else None,
            note=note,
        ))
        return saved
