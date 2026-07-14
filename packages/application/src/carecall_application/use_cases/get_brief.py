from typing import Optional

from carecall_domain import Brief

from ..ports.repositories import BriefRepository


class GetBriefUseCase:
    def __init__(self, brief_repository: BriefRepository):
        self.brief_repository = brief_repository

    def execute(self, brief_id: str) -> Optional[Brief]:
        return self.brief_repository.get(brief_id)
