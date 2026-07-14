from typing import List

from carecall_domain import Call

from ..ports.repositories import CallRepository


class ListCallsUseCase:
    def __init__(self, call_repository: CallRepository):
        self.call_repository = call_repository

    def execute(self) -> List[Call]:
        return self.call_repository.list_calls()
