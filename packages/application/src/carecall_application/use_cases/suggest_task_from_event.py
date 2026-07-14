from typing import Optional

from carecall_domain import CoordinatorTask, suggest_task_draft

from ..ports.repositories import CoordinatorTaskRepository, TimelineEventRepository
from .create_task import CreateTaskUseCase


class SuggestTaskFromEventUseCase:
    """Turns a timeline event into a suggested task - always is_suggested,
    always linked to the exact source evidence, and idempotent: calling this
    again for the same event returns the existing suggestion rather than
    creating a duplicate."""

    def __init__(
        self,
        timeline_event_repository: TimelineEventRepository,
        task_repository: CoordinatorTaskRepository,
        create_task: CreateTaskUseCase,
    ):
        self.timeline_event_repository = timeline_event_repository
        self.task_repository = task_repository
        self.create_task = create_task

    def execute(self, event_id: str) -> Optional[CoordinatorTask]:
        event = self.timeline_event_repository.get(event_id)
        if event is None:
            return None

        draft = suggest_task_draft(event)
        if draft is None:
            return None

        dedupe_key = f"suggested:{event_id}"
        existing = self.task_repository.find_by_dedupe_key(event.patient_id, dedupe_key)
        if existing is not None:
            return existing

        return self.create_task.execute(
            title=draft.title,
            description=draft.description,
            patient_id=event.patient_id,
            priority=draft.priority,
            category=draft.category,
            created_by="system",
            source_event_id=event.event_id,
            source_call_id=event.source_call_id,
            source_turn_start=event.source_turn_start,
            source_turn_end=event.source_turn_end,
            is_suggested=True,
            dedupe_key=dedupe_key,
        )
