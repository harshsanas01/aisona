from typing import List, Optional

from carecall_domain import CoordinatorTask

from ..ports.repositories import CoordinatorTaskRepository


class ListTasksUseCase:
    def __init__(self, task_repository: CoordinatorTaskRepository):
        self.task_repository = task_repository

    def execute(
        self,
        *,
        patient_id: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        assignee: Optional[str] = None,
    ) -> List[CoordinatorTask]:
        return self.task_repository.list_tasks(
            patient_id=patient_id, status=status, priority=priority, category=category, assignee=assignee,
        )
