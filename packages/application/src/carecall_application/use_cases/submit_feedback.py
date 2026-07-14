import uuid
from datetime import datetime, timezone
from typing import Optional

from carecall_domain import FEEDBACK_CATEGORIES_BY_TARGET_TYPE, Feedback, InvalidFeedbackError

from ..ports.repositories import FeedbackRepository
from .update_pattern import UpdatePatternUseCase
from .update_person_mention import UpdatePersonMentionUseCase
from .update_timeline_event import UpdateTimelineEventUseCase

# Feedback categories that also update the underlying entity's own
# review_status/reviewed_status, keeping current-state in sync with the
# feedback history. "merge_duplicate" has no automated effect - there is no
# duplicate-merge workflow yet, so it is recorded for a human to act on.
_REVIEW_STATUS_FOR_CATEGORY = {"confirm": "confirmed", "correct": "corrected", "dismiss": "dismissed"}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SubmitFeedbackUseCase:
    def __init__(
        self,
        feedback_repository: FeedbackRepository,
        update_timeline_event: Optional[UpdateTimelineEventUseCase] = None,
        update_pattern: Optional[UpdatePatternUseCase] = None,
        update_person_mention: Optional[UpdatePersonMentionUseCase] = None,
    ):
        self.feedback_repository = feedback_repository
        self.update_timeline_event = update_timeline_event
        self.update_pattern = update_pattern
        self.update_person_mention = update_person_mention

    def execute(
        self,
        *,
        target_type: str,
        target_id: str,
        category: str,
        actor: str,
        comment: Optional[str] = None,
        corrected_value: Optional[str] = None,
        prompt_version: Optional[str] = None,
        retrieval_version: Optional[str] = None,
        model_version: Optional[str] = None,
    ) -> Feedback:
        allowed_categories = FEEDBACK_CATEGORIES_BY_TARGET_TYPE.get(target_type)
        if allowed_categories is None:
            raise InvalidFeedbackError(
                f"'{target_type}' is not a valid target_type; "
                f"must be one of {tuple(FEEDBACK_CATEGORIES_BY_TARGET_TYPE)}"
            )
        if category not in allowed_categories:
            raise InvalidFeedbackError(
                f"'{category}' is not a valid category for target_type '{target_type}'; "
                f"must be one of {allowed_categories}"
            )

        feedback = Feedback(
            feedback_id=f"fb-{uuid.uuid4().hex[:12]}",
            target_type=target_type,
            target_id=target_id,
            category=category,
            actor=actor,
            created_at=_utcnow_iso(),
            comment=comment,
            corrected_value=corrected_value,
            prompt_version=prompt_version,
            retrieval_version=retrieval_version,
            model_version=model_version,
        )
        created = self.feedback_repository.create(feedback)
        self._sync_review_status(target_type, target_id, category, corrected_value)
        return created

    def _sync_review_status(
        self, target_type: str, target_id: str, category: str, corrected_value: Optional[str],
    ) -> None:
        review_status = _REVIEW_STATUS_FOR_CATEGORY.get(category)
        if review_status is None:
            return
        if target_type == "timeline_event" and self.update_timeline_event is not None:
            self.update_timeline_event.execute(
                target_id, review_status, description=corrected_value if category == "correct" else None,
            )
        elif target_type == "pattern" and self.update_pattern is not None:
            self.update_pattern.execute(target_id, review_status)
        elif target_type == "person_mention" and self.update_person_mention is not None:
            # corrected_value is free text, not a validated relationship_type/name -
            # promoting a mention's relationship_type (e.g. to "participant") only
            # happens through the dedicated PATCH endpoint, never through this
            # generic feedback path.
            self.update_person_mention.execute(target_id, review_status)
