from abc import ABC, abstractmethod
from datetime import date, datetime, timezone
from typing import Dict, List

from ..entities.patient_pattern import PatientPattern
from ..entities.pattern_evidence_ref import PatternEvidenceRef
from ..entities.timeline_event import TimelineEvent

DETECTOR_VERSION = "v1"

# Maps each timeline event_type onto a coarser "concern key" for grouping.
# symptom_reported and symptom_recurrence are two different *extraction*
# labels for the same underlying concern (first mention vs. a mention that
# says "again") - they must count as one concern for pattern purposes, or a
# single symptom would be double-counted as both a "repeated_occurrence" and
# a separate spurious "first_occurrence". Administrative categories
# (appointment_request, assistive_device_update, follow_up_promised,
# issue_resolved) are handled separately, not treated as recurring concerns.
_CONCERN_KEY_FOR_EVENT_TYPE = {
    "medication_adherence_concern": "medication_adherence_concern",
    "symptom_reported": "symptom",
    "symptom_recurrence": "symptom",
    "sleep_issue": "sleep_issue",
    "meal_concern": "meal_concern",
    "transportation_issue": "transportation_issue",
    "home_safety_concern": "home_safety_concern",
}
_CONCERN_EVENT_TYPES = tuple(_CONCERN_KEY_FOR_EVENT_TYPE)
_CONCERN_KEYS = tuple(dict.fromkeys(_CONCERN_KEY_FOR_EVENT_TYPE.values()))

_REPEATED_PATTERN_TYPE = {
    "transportation_issue": "repeated_transportation_issue",
    "medication_adherence_concern": "repeated_missed_medication",
    "sleep_issue": "repeated_sleep_issue",
    "meal_concern": "repeated_meal_concern",
}

_LABELS = {
    "medication_adherence_concern": "a possible missed medication",
    "symptom": "a reported symptom",
    "sleep_issue": "a sleep issue",
    "meal_concern": "a meal or appetite concern",
    "transportation_issue": "a transportation issue",
    "home_safety_concern": "a home-safety concern",
}

_WORSENING_INTENSIFIERS = (
    "worse", "much worse", "more often", "every day", "constant", "constantly",
    "severe", "can't", "unbearable", "getting worse", "worse than",
)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_date(iso_date: str) -> date:
    return datetime.strptime(iso_date, "%Y-%m-%d").date()


def _label(event_type: str) -> str:
    return _LABELS.get(event_type, event_type.replace("_", " "))


def _collapse_by_call(events: List[TimelineEvent]) -> List[TimelineEvent]:
    """Two turns in the same call reporting the same concern are one
    occurrence, not two - patterns count distinct contacts, not raw turns."""
    by_call: Dict[str, TimelineEvent] = {}
    for event in sorted(events, key=lambda e: (e.observed_date, e.source_turn_start)):
        by_call.setdefault(event.source_call_id, event)
    return sorted(by_call.values(), key=lambda e: e.observed_date)


def _evidence_for(events: List[TimelineEvent]) -> tuple:
    return tuple(
        PatternEvidenceRef(
            timeline_event_id=e.event_id, call_id=e.source_call_id,
            turn_start=e.source_turn_start, turn_end=e.source_turn_end, quote=e.quote,
        )
        for e in events
    )


def _has_new_intensifier(first_quote: str, latest_quote: str) -> bool:
    first_lower, latest_lower = first_quote.lower(), latest_quote.lower()
    return any(word in latest_lower and word not in first_lower for word in _WORSENING_INTENSIFIERS)


def _build_pattern(
    patient_id: str,
    pattern_type: str,
    title: str,
    summary: str,
    status: str,
    severity: str,
    occurrences: List[TimelineEvent],
) -> PatientPattern:
    now = _utcnow_iso()
    dates = sorted(e.observed_date for e in occurrences)
    call_ids = tuple(dict.fromkeys(e.source_call_id for e in occurrences))
    return PatientPattern(
        pattern_id=f"pat-{patient_id}-{pattern_type}-{occurrences[0].source_call_id}",
        patient_id=patient_id,
        pattern_type=pattern_type,
        title=title,
        summary=summary,
        status=status,
        severity=severity,
        first_observed_date=dates[0],
        latest_observed_date=dates[-1],
        related_timeline_event_ids=tuple(e.event_id for e in occurrences),
        related_call_ids=call_ids,
        evidence=_evidence_for(occurrences),
        detector_version=DETECTOR_VERSION,
        reviewed_status="unreviewed",
        created_at=now,
        updated_at=now,
        dedupe_key=f"{pattern_type}:{occurrences[0].source_call_id}",
    )


class PatternDetector(ABC):
    """Detects evidence-based longitudinal patterns from a patient's already
    -extracted timeline events - never from raw transcripts directly (see
    ADR: structured events before LLM summaries). Deterministic rules are
    the required, always-available implementation. An optional LLM stage
    may only rephrase/summarize patterns this detector already found; it
    can never invent a pattern on its own."""

    @abstractmethod
    def detect(self, patient_id: str, events: List[TimelineEvent]) -> List[PatientPattern]: ...


class DeterministicPatternDetector(PatternDetector):
    def detect(self, patient_id: str, events: List[TimelineEvent]) -> List[PatientPattern]:
        patterns: List[PatientPattern] = []
        patterns.extend(self._concern_frequency_patterns(patient_id, events))
        patterns.extend(self._medication_before_symptom_patterns(patient_id, events))
        patterns.extend(self._resolution_patterns(patient_id, events))
        return patterns

    def _concern_frequency_patterns(self, patient_id: str, events: List[TimelineEvent]) -> List[PatientPattern]:
        patterns: List[PatientPattern] = []
        for concern_key in _CONCERN_KEYS:
            occurrences = _collapse_by_call([
                e for e in events if _CONCERN_KEY_FOR_EVENT_TYPE.get(e.event_type) == concern_key
            ])
            if not occurrences:
                continue
            label = _label(concern_key)

            if len(occurrences) == 1:
                event = occurrences[0]
                patterns.append(_build_pattern(
                    patient_id, "first_occurrence",
                    f"First reported: {label}",
                    f"Observed pattern: {label} was first reported on {event.observed_date} "
                    f"(call {event.source_call_id}). Requires staff review.",
                    "active", "informational", occurrences,
                ))
                continue

            gaps = [
                (_parse_date(b.observed_date) - _parse_date(a.observed_date)).days
                for a, b in zip(occurrences, occurrences[1:])
            ]
            first_quote, latest_quote = occurrences[0].quote, occurrences[-1].quote
            call_list = ", ".join(dict.fromkeys(e.source_call_id for e in occurrences))

            if len(occurrences) >= 3 and gaps[-1] < gaps[0]:
                patterns.append(_build_pattern(
                    patient_id, "increasing_frequency",
                    f"Increasing frequency: {label}",
                    f"Observed pattern: {label} was reported {len(occurrences)} times with decreasing "
                    f"time between reports (from {occurrences[0].observed_date} to "
                    f"{occurrences[-1].observed_date}, across calls {call_list}). Requires staff review.",
                    "active", "high_attention", occurrences,
                ))
            elif _has_new_intensifier(first_quote, latest_quote):
                patterns.append(_build_pattern(
                    patient_id, "worsening_wording",
                    f"Possible worsening: {label}",
                    f"Observed pattern: the most recent report of {label} "
                    f"(call {occurrences[-1].source_call_id}, {occurrences[-1].observed_date}) uses more "
                    f"severe wording than the first report (call {occurrences[0].source_call_id}, "
                    f"{occurrences[0].observed_date}). Requires staff review.",
                    "active", "high_attention", occurrences,
                ))
            else:
                pattern_type = _REPEATED_PATTERN_TYPE.get(concern_key, "repeated_occurrence")
                patterns.append(_build_pattern(
                    patient_id, pattern_type,
                    f"Repeated: {label} ({len(occurrences)} occurrences)",
                    f"Observed pattern: {label} was reported {len(occurrences)} times between "
                    f"{occurrences[0].observed_date} and {occurrences[-1].observed_date}, "
                    f"across calls {call_list}. Requires staff review.",
                    "active", "attention", occurrences,
                ))
        return patterns

    def _medication_before_symptom_patterns(
        self, patient_id: str, events: List[TimelineEvent],
    ) -> List[PatientPattern]:
        patterns: List[PatientPattern] = []
        medication_events = _collapse_by_call([e for e in events if e.event_type == "medication_started"])
        symptom_events = _collapse_by_call(
            [e for e in events if e.event_type in ("symptom_reported", "symptom_recurrence")]
        )
        for medication in medication_events:
            later_symptoms = [
                s for s in symptom_events if _parse_date(s.observed_date) > _parse_date(medication.observed_date)
            ]
            if not later_symptoms:
                continue
            symptom = later_symptoms[0]
            symptom_label = _label(_CONCERN_KEY_FOR_EVENT_TYPE.get(symptom.event_type, symptom.event_type))
            patterns.append(_build_pattern(
                patient_id, "medication_started_before_symptom",
                "Symptom reported after a new medication was started",
                f"Observed pattern: {symptom_label} was first reported on {symptom.observed_date} "
                f"(call {symptom.source_call_id}), after a new medication was reported started on "
                f"{medication.observed_date} (call {medication.source_call_id}). This is a temporal "
                "observation only, not a causal or clinical conclusion. Requires staff review.",
                "uncertain", "attention", [medication, symptom],
            ))
        return patterns

    def _resolution_patterns(self, patient_id: str, events: List[TimelineEvent]) -> List[PatientPattern]:
        patterns: List[PatientPattern] = []
        concern_occurrences = _collapse_by_call([e for e in events if e.event_type in _CONCERN_EVENT_TYPES])
        resolution_events = _collapse_by_call([e for e in events if e.event_type == "issue_resolved"])
        claimed_concern_ids = set()

        for resolution in resolution_events:
            resolution_date = _parse_date(resolution.observed_date)
            prior_concerns = [
                c for c in concern_occurrences
                if _parse_date(c.observed_date) <= resolution_date and c.event_id not in claimed_concern_ids
            ]
            if not prior_concerns:
                continue
            resolved_concern = prior_concerns[-1]
            claimed_concern_ids.add(resolved_concern.event_id)
            resolved_concern_key = _CONCERN_KEY_FOR_EVENT_TYPE.get(resolved_concern.event_type, resolved_concern.event_type)
            concern_label = _label(resolved_concern_key)

            later_same_concern = [
                c for c in concern_occurrences
                if _CONCERN_KEY_FOR_EVENT_TYPE.get(c.event_type, c.event_type) == resolved_concern_key
                and _parse_date(c.observed_date) > resolution_date
            ]
            if later_same_concern:
                recurrence = later_same_concern[0]
                patterns.append(_build_pattern(
                    patient_id, "recurrence_after_resolution",
                    f"Recurrence after apparent resolution: {concern_label}",
                    f"Observed pattern: {concern_label} was reported resolved on "
                    f"{resolution.observed_date} (call {resolution.source_call_id}), but recurred on "
                    f"{recurrence.observed_date} (call {recurrence.source_call_id}). Requires staff review.",
                    "active", "high_attention", [resolved_concern, resolution, recurrence],
                ))
            else:
                patterns.append(_build_pattern(
                    patient_id, "issue_resolved",
                    f"Issue resolved: {concern_label}",
                    f"Observed pattern: {concern_label} reported on "
                    f"{resolved_concern.observed_date} (call {resolved_concern.source_call_id}) appears "
                    f"resolved as of {resolution.observed_date} (call {resolution.source_call_id}). "
                    "Requires staff review to confirm.",
                    "resolved", "informational", [resolved_concern, resolution],
                ))
        return patterns
