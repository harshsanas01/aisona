from dataclasses import dataclass, field
from typing import Dict

from ..ports.repositories import FeedbackRepository

# Large enough to cover any realistic feedback volume for a single-deployment
# demo/pilot without needing pagination in the summary aggregation itself.
_SUMMARY_SCAN_LIMIT = 10_000


@dataclass(frozen=True)
class FeedbackSummary:
    total: int
    by_target_type: Dict[str, int] = field(default_factory=dict)
    by_category: Dict[str, int] = field(default_factory=dict)


class GetFeedbackSummaryUseCase:
    def __init__(self, feedback_repository: FeedbackRepository):
        self.feedback_repository = feedback_repository

    def execute(self) -> FeedbackSummary:
        records = self.feedback_repository.list_feedback(limit=_SUMMARY_SCAN_LIMIT)
        by_target_type: Dict[str, int] = {}
        by_category: Dict[str, int] = {}
        for record in records:
            by_target_type[record.target_type] = by_target_type.get(record.target_type, 0) + 1
            by_category[record.category] = by_category.get(record.category, 0) + 1
        return FeedbackSummary(total=len(records), by_target_type=by_target_type, by_category=by_category)
