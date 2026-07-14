from typing import List, Optional

from carecall_domain import PersonMention

from ..ports.repositories import PersonMentionRepository


class GetPatientPersonMentionsUseCase:
    def __init__(self, person_mention_repository: PersonMentionRepository):
        self.person_mention_repository = person_mention_repository

    def execute(
        self, patient_id: str, *, relationship_type: Optional[str] = None, review_status: Optional[str] = None,
    ) -> List[PersonMention]:
        mentions = self.person_mention_repository.list_for_patient(patient_id)
        if relationship_type:
            mentions = [m for m in mentions if m.relationship_type == relationship_type]
        if review_status:
            mentions = [m for m in mentions if m.review_status == review_status]
        return sorted(mentions, key=lambda m: (m.source_call_id, m.source_turn))
