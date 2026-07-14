from typing import List, Optional

from carecall_domain import TimelineEvent

from ..ports.repositories import TimelineEventRepository


class GetPatientTimelineUseCase:
    def __init__(self, timeline_event_repository: TimelineEventRepository):
        self.timeline_event_repository = timeline_event_repository

    def execute(
        self, patient_id: str, *, event_type: Optional[str] = None, review_status: Optional[str] = None,
    ) -> List[TimelineEvent]:
        events = self.timeline_event_repository.list_for_patient(patient_id)
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if review_status:
            events = [e for e in events if e.review_status == review_status]
        return sorted(events, key=lambda e: (e.observed_date, e.source_turn_start))
