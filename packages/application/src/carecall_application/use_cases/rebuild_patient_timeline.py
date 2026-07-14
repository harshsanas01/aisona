from typing import List

from carecall_domain import TimelineEvent, TimelineExtractor

from ..ports.repositories import CallRepository, TimelineEventRepository


class RebuildPatientTimelineUseCase:
    """Re-runs extraction over every one of a patient's calls and upserts the
    result. Idempotent and safe to call repeatedly: TimelineEventRepository
    matches on (source_call_id, dedupe_key) and never overwrites an event a
    coordinator has already reviewed - see
    docs/architecture/event-extraction.md."""

    def __init__(
        self,
        call_repository: CallRepository,
        timeline_event_repository: TimelineEventRepository,
        extractor: TimelineExtractor,
    ):
        self.call_repository = call_repository
        self.timeline_event_repository = timeline_event_repository
        self.extractor = extractor

    def execute(self, patient_id: str) -> List[TimelineEvent]:
        calls = [c for c in self.call_repository.list_calls() if c.patient.id == patient_id]
        extracted: List[TimelineEvent] = []
        for call in calls:
            extracted.extend(self.extractor.extract(call))
        self.timeline_event_repository.upsert_many(extracted)
        return self.timeline_event_repository.list_for_patient(patient_id)
