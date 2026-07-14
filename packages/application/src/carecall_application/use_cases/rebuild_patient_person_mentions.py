from typing import List

from carecall_domain import PersonMention, PersonMentionExtractor

from ..ports.repositories import CallRepository, PersonMentionRepository


class RebuildPatientPersonMentionsUseCase:
    """Re-runs extraction over every one of a patient's calls and upserts the
    result. Idempotent and safe to call repeatedly: PersonMentionRepository
    matches on (source_call_id, dedupe_key) and never overwrites a mention a
    coordinator has already reviewed."""

    def __init__(
        self,
        call_repository: CallRepository,
        person_mention_repository: PersonMentionRepository,
        extractor: PersonMentionExtractor,
    ):
        self.call_repository = call_repository
        self.person_mention_repository = person_mention_repository
        self.extractor = extractor

    def execute(self, patient_id: str) -> List[PersonMention]:
        calls = [c for c in self.call_repository.list_calls() if c.patient.id == patient_id]
        extracted: List[PersonMention] = []
        for call in calls:
            extracted.extend(self.extractor.extract(call))
        self.person_mention_repository.upsert_many(extracted)
        return self.person_mention_repository.list_for_patient(patient_id)
