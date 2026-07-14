from typing import List

from carecall_domain import PatientPattern, PatternDetector

from ..ports.repositories import PatternRepository, TimelineEventRepository


class RebuildPatientPatternsUseCase:
    """Detects patterns from a patient's already-extracted timeline events
    (never from raw transcripts directly) and upserts the result.
    Idempotent: PatternRepository matches on (patient_id, dedupe_key) and
    never overwrites a pattern a coordinator has already reviewed."""

    def __init__(
        self,
        timeline_event_repository: TimelineEventRepository,
        pattern_repository: PatternRepository,
        detector: PatternDetector,
    ):
        self.timeline_event_repository = timeline_event_repository
        self.pattern_repository = pattern_repository
        self.detector = detector

    def execute(self, patient_id: str) -> List[PatientPattern]:
        events = self.timeline_event_repository.list_for_patient(patient_id)
        detected = self.detector.detect(patient_id, events)
        self.pattern_repository.upsert_many(detected)
        return self.pattern_repository.list_for_patient(patient_id)
