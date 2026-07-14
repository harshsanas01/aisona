from typing import Optional

from carecall_domain import (
    PERSON_MENTION_REVIEW_STATUSES,
    PERSON_RELATIONSHIP_TYPES,
    InvalidReviewStatusError,
    PersonMention,
)

from ..ports.repositories import PersonMentionRepository


class UpdatePersonMentionUseCase:
    """The only way a person mention's review_status changes - extraction
    never marks a mention confirmed/corrected/dismissed itself. This is also
    the only path by which a mention can be promoted to relationship_type
    "participant" - the extractor never assigns it (see PersonMention's
    docstring)."""

    def __init__(self, person_mention_repository: PersonMentionRepository):
        self.person_mention_repository = person_mention_repository

    def execute(
        self,
        mention_id: str,
        review_status: str,
        *,
        corrected_relationship_type: Optional[str] = None,
        corrected_name: Optional[str] = None,
    ) -> Optional[PersonMention]:
        if review_status not in PERSON_MENTION_REVIEW_STATUSES:
            raise InvalidReviewStatusError(
                f"'{review_status}' is not a valid review_status; must be one of {PERSON_MENTION_REVIEW_STATUSES}"
            )
        if corrected_relationship_type is not None and corrected_relationship_type not in PERSON_RELATIONSHIP_TYPES:
            raise InvalidReviewStatusError(
                f"'{corrected_relationship_type}' is not a valid relationship_type; "
                f"must be one of {PERSON_RELATIONSHIP_TYPES}"
            )
        return self.person_mention_repository.update_review_status(
            mention_id,
            review_status,
            corrected_relationship_type=corrected_relationship_type,
            corrected_name=corrected_name,
        )
