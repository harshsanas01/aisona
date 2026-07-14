from typing import Optional

from carecall_domain import QuestionAudit

from ..ports.repositories import QuestionAuditRepository


class GetQuestionAuditUseCase:
    def __init__(self, audit_repository: QuestionAuditRepository):
        self.audit_repository = audit_repository

    def execute(self, request_id: str) -> Optional[QuestionAudit]:
        return self.audit_repository.get(request_id)
