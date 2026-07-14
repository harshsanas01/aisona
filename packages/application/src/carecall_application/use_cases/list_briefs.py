from typing import List, Optional

from carecall_domain import Brief

from ..ports.repositories import BriefRepository


class ListBriefsUseCase:
    def __init__(self, brief_repository: BriefRepository):
        self.brief_repository = brief_repository

    def execute(self, *, brief_type: Optional[str] = None, patient_id: Optional[str] = None) -> List[Brief]:
        return self.brief_repository.list_briefs(brief_type=brief_type, patient_id=patient_id)
