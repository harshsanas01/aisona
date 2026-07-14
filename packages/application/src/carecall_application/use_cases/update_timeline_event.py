from typing import Optional

from carecall_domain import TIMELINE_REVIEW_STATUSES, InvalidReviewStatusError, TimelineEvent

from ..ports.repositories import TimelineEventRepository


class UpdateTimelineEventUseCase:
    """The only way a timeline event's review_status changes - extraction
    (deterministic or LLM) never sets anything but "unreviewed" itself.
    This is always a human coordinator's decision."""

    def __init__(self, timeline_event_repository: TimelineEventRepository):
        self.timeline_event_repository = timeline_event_repository

    def execute(
        self,
        event_id: str,
        review_status: str,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[TimelineEvent]:
        if review_status not in TIMELINE_REVIEW_STATUSES:
            raise InvalidReviewStatusError(
                f"'{review_status}' is not a valid review_status; must be one of {TIMELINE_REVIEW_STATUSES}"
            )
        return self.timeline_event_repository.update_review_status(
            event_id, review_status, title=title, description=description,
        )
