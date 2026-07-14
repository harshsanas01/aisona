from typing import List, Optional

from carecall_domain import Feedback

from ..ports.repositories import FeedbackRepository


class ListFeedbackUseCase:
    def __init__(self, feedback_repository: FeedbackRepository):
        self.feedback_repository = feedback_repository

    def execute(
        self,
        *,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100,
    ) -> List[Feedback]:
        return self.feedback_repository.list_feedback(
            target_type=target_type, target_id=target_id, category=category, limit=limit,
        )
