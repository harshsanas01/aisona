import hashlib
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional

from ..entities.timeline_event import TimelineEvent
from ..entities.transcript import Call
from .safety_classifier import DeterministicSafetyClassifier

# Every value here is a real, verifiable read of the transcript - never a
# clinical judgment. A missed dose is reported as "missed_medication", not as
# "non-adherence"; a fall is reported as "home_safety_concern", not
# diagnosed. See docs/architecture/event-extraction.md.
_SAFETY_CATEGORY_TO_EVENT_TYPE = {
    "dizziness": "symptom_reported",
    "fall_or_near_fall": "home_safety_concern",
    "missed_medication": "medication_adherence_concern",
    "sleep_problem": "sleep_issue",
    "food_or_meal_concern": "meal_concern",
    "glucose_concern": "symptom_reported",
    "respiratory_symptom": "symptom_reported",
    "transportation_issue": "transportation_issue",
    "home_safety_concern": "home_safety_concern",
}

# "medication_change" covers both starting and stopping/adjusting a
# medication, but the timeline vocabulary only has a "medication_started"
# type - only these specific trigger phrases actually describe a new
# medication being started; "stopped taking"/"changed my dosage"/"dosage
# change" describe something the vocabulary has no event type for yet, so
# they are deliberately not turned into a (mislabeled) timeline event. Bare
# "new pill" is deliberately excluded even though the safety classifier
# triggers on it - it also matches a participant wondering out loud whether
# an existing pill might be behind a symptom (e.g. "could it be the new
# pill?"), which is not itself a report that a medication was started.
_MEDICATION_STARTED_TRIGGERS = {
    "started me on a new", "new blood pressure pill", "new medication",
}

_RECURRENCE_MARKERS = ("again", "happened again", "keeps happening", "keeps coming back", "back again")

# Categories not covered by the safety classifier at all - each is a plain
# keyword match against the participant's (or, for follow-up commitments,
# the assistant's) own words, grounded in real transcript phrasing rather
# than invented examples.
_EXTRA_RULES = [
    ("appointment_request", "participant",
     ["need some help with an appointment", "need to reschedule", "can it be moved", "i'm scheduled for"]),
    ("assistive_device_update", "participant",
     ["new walker", "grab bar", "hearing aid", "new cane", "wheelchair"]),
    ("issue_resolved", "participant",
     ["no more guessing", "no mystery", "all set now", "working out now",
      "no longer having", "cleared up", "back to normal"]),
    ("follow_up_promised", "assistant",
     ["i'll flag", "i'm going to flag", "flagging this", "i'll report", "i'll pass it to",
      "i'll let the nurse know", "i'll mention it to the nurse", "i'll make sure the nurse knows",
      "nurse will call you", "she will call you", "i'll ask the nurse"]),
]

_TITLES = {
    "medication_started": "New medication started",
    "medication_adherence_concern": "Possible missed medication",
    "symptom_reported": "Symptom reported",
    "symptom_recurrence": "Symptom reported again",
    "sleep_issue": "Sleep issue reported",
    "meal_concern": "Meal or appetite concern reported",
    "transportation_issue": "Transportation issue reported",
    "appointment_request": "Appointment request",
    "home_safety_concern": "Home safety concern observed",
    "assistive_device_update": "Assistive device update",
    "issue_resolved": "Previously reported issue appears resolved",
    "follow_up_promised": "Staff follow-up commitment recorded",
    "other_safety_event": "Other safety-relevant event observed",
}

_DESCRIPTIONS = {
    "medication_started": "Observed pattern: a new medication was reported as started. Requires staff review.",
    "medication_adherence_concern": "Observed pattern: a potential missed dose was reported. Requires staff review.",
    "symptom_reported": "Observed pattern: a symptom was reported in the transcript. Requires staff review.",
    "symptom_recurrence": (
        "Observed pattern: a previously reported symptom appears to have recurred. Requires staff review."
    ),
    "sleep_issue": "Observed pattern: a sleep-related concern was reported in the transcript.",
    "meal_concern": "Observed pattern: a meal or appetite concern was reported in the transcript.",
    "transportation_issue": "Observed pattern: a transportation issue was reported in the transcript.",
    "appointment_request": "Observed pattern: an appointment scheduling request was reported in the transcript.",
    "home_safety_concern": "Observed pattern: a home-safety concern was reported in the transcript. Requires staff review.",
    "assistive_device_update": "Observed pattern: an assistive-device update was reported in the transcript.",
    "issue_resolved": (
        "Observed pattern: a previously reported issue appears resolved per the transcript. "
        "Requires staff review to confirm."
    ),
    "follow_up_promised": "Observed pattern: a staff follow-up commitment was recorded in the transcript.",
    "other_safety_event": "Observed pattern: another safety-relevant event was observed. Requires staff review.",
}


class TimelineExtractor(ABC):
    """Turns a single call's transcript into candidate patient-timeline
    events - "observed transcript events", never a diagnosis. Deterministic
    rules are the required, always-available implementation (must work
    fully offline); an LLM-backed extractor may implement this same
    interface, but per docs/architecture/event-extraction.md its output
    must still have every citation field (call_id, turn range, quote)
    reconstructed by server code from the real transcript, never trusted
    verbatim from the model."""

    @abstractmethod
    def extract(self, call: Call) -> List[TimelineEvent]: ...


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_timeline_event(
    call: Call,
    turn_number: int,
    event_type: str,
    quote: str,
    *,
    confidence: str = "medium",
    extraction_method: str = "deterministic",
) -> TimelineEvent:
    """Shared citation-reconstruction helper: every field that identifies
    *where the evidence came from* (call, turn, quote) is taken directly
    from the real Call object, never from an extractor's own claim - this is
    what "server-owned citation reconstruction" means for an LLM-backed
    extractor (see docs/architecture/event-extraction.md and ADR 0003)."""
    now = _utcnow_iso()
    dedupe_key = f"{event_type}:{turn_number}"
    event_id = f"evt-{call.call_id}-{turn_number}-{event_type}"
    return TimelineEvent(
        event_id=event_id,
        patient_id=call.patient.id,
        event_type=event_type,
        title=_TITLES[event_type],
        description=_DESCRIPTIONS[event_type],
        observed_date=call.date,
        source_call_id=call.call_id,
        source_turn_start=turn_number,
        source_turn_end=turn_number,
        quote=quote,
        confidence=confidence,
        extraction_method=extraction_method,
        review_status="unreviewed",
        created_at=now,
        updated_at=now,
        dedupe_key=dedupe_key,
    )


def _make_event(
    call: Call, turn_number: int, event_type: str, quote: str, *, confidence: str = "medium",
) -> TimelineEvent:
    return build_timeline_event(call, turn_number, event_type, quote, confidence=confidence)


class DeterministicTimelineExtractor(TimelineExtractor):
    """Required, always-available extractor. Reuses DeterministicSafetyClassifier
    for the categories it already covers (this keeps the two feature's
    behavior consistent and avoids re-deriving the same turn-matching rules
    twice), then applies a small set of additional keyword rules for
    categories the safety classifier has no equivalent for."""

    def __init__(self) -> None:
        self._safety_classifier = DeterministicSafetyClassifier()

    def extract(self, call: Call) -> List[TimelineEvent]:
        events: List[TimelineEvent] = []
        seen_dedupe_keys = set()

        for safety_event in self._safety_classifier.classify(call):
            event_type = self._map_safety_category(safety_event.category, safety_event.explanation)
            if event_type is None:
                continue
            if _has_recurrence_marker(safety_event.matched_text) and event_type == "symptom_reported":
                event_type = "symptom_recurrence"
            event = _make_event(call, safety_event.turn_number, event_type, safety_event.matched_text)
            if event.dedupe_key in seen_dedupe_keys:
                continue
            seen_dedupe_keys.add(event.dedupe_key)
            events.append(event)

        for turn_number, turn in enumerate(call.turns, start=1):
            lowered = turn.text.lower()
            for event_type, speaker, triggers in _EXTRA_RULES:
                if turn.speaker != speaker:
                    continue
                if not any(t in lowered for t in triggers):
                    continue
                event = _make_event(call, turn_number, event_type, turn.text)
                if event.dedupe_key in seen_dedupe_keys:
                    continue
                seen_dedupe_keys.add(event.dedupe_key)
                events.append(event)

        return events

    @staticmethod
    def _map_safety_category(category: str, explanation: str) -> Optional[str]:
        if category == "medication_change":
            matched_trigger = explanation.split("'")[1] if "'" in explanation else ""
            return "medication_started" if matched_trigger in _MEDICATION_STARTED_TRIGGERS else None
        return _SAFETY_CATEGORY_TO_EVENT_TYPE.get(category)


def _has_recurrence_marker(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in _RECURRENCE_MARKERS)


def content_hash(*parts: str) -> str:
    """Stable hash helper for extractors that need a dedupe key derived from
    content rather than turn position (e.g. an LLM extractor whose turn
    ranges may shift slightly between runs)."""
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]
