from typing import Optional

from carecall_domain import PATTERN_REVIEW_STATUSES, InvalidReviewStatusError, PatientPattern

from ..ports.repositories import PatternRepository


class UpdatePatternUseCase:
    """The only way a pattern's reviewed_status changes - detection never
    sets anything but "unreviewed" itself. Always a human coordinator's
    decision."""

    def __init__(self, pattern_repository: PatternRepository):
        self.pattern_repository = pattern_repository

    def execute(self, pattern_id: str, reviewed_status: str) -> Optional[PatientPattern]:
        if reviewed_status not in PATTERN_REVIEW_STATUSES:
            raise InvalidReviewStatusError(
                f"'{reviewed_status}' is not a valid reviewed_status; must be one of {PATTERN_REVIEW_STATUSES}"
            )
        return self.pattern_repository.update_reviewed_status(pattern_id, reviewed_status)
