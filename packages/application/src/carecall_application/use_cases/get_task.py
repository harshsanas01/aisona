from typing import List, Optional, Tuple

from carecall_domain import CoordinatorTask, TaskActivity

from ..ports.repositories import CoordinatorTaskRepository, TaskActivityRepository


class GetTaskUseCase:
    def __init__(self, task_repository: CoordinatorTaskRepository, activity_repository: TaskActivityRepository):
        self.task_repository = task_repository
        self.activity_repository = activity_repository

    def execute(self, task_id: str) -> Optional[Tuple[CoordinatorTask, List[TaskActivity]]]:
        task = self.task_repository.get(task_id)
        if task is None:
            return None
        return task, self.activity_repository.list_for_task(task_id)
