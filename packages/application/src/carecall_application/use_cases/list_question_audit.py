from typing import List, Optional

from carecall_domain import QuestionAudit

from ..ports.repositories import QuestionAuditRepository


class ListQuestionAuditUseCase:
    def __init__(self, audit_repository: QuestionAuditRepository):
        self.audit_repository = audit_repository

    def execute(self, *, answerable: Optional[bool] = None, limit: int = 50) -> List[QuestionAudit]:
        return self.audit_repository.list_records(answerable=answerable, limit=limit)
