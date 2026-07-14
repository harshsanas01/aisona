from typing import List, Optional

from carecall_domain import SafetyClassifier, SafetyEvent

from ..ports.repositories import CallRepository


class ListSafetyEventsUseCase:
    """Runs the configured SafetyClassifier over every stored call. Cheap
    enough to compute on demand (deterministic regex rules over a small
    transcript corpus) rather than persisting a safety_events table."""

    def __init__(self, call_repository: CallRepository, classifier: SafetyClassifier):
        self.call_repository = call_repository
        self.classifier = classifier

    def execute(self, *, call_id: Optional[str] = None, category: Optional[str] = None) -> List[SafetyEvent]:
        calls = self.call_repository.list_calls()
        if call_id:
            calls = [c for c in calls if c.call_id == call_id]

        events: List[SafetyEvent] = []
        for call in calls:
            events.extend(self.classifier.classify(call))

        if category:
            events = [e for e in events if e.category == category]
        return events
