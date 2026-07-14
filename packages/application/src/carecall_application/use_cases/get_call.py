from typing import Optional

from carecall_domain import Call

from ..ports.repositories import CallRepository


class GetCallUseCase:
    def __init__(self, call_repository: CallRepository):
        self.call_repository = call_repository

    def execute(self, call_id: str) -> Optional[Call]:
        return self.call_repository.get_call(call_id)
