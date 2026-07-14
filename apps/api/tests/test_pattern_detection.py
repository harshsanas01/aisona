from pathlib import Path
from typing import List

from carecall_domain import DeterministicPatternDetector, DeterministicTimelineExtractor, TimelineEvent
from carecall_persistence.in_memory.loader import load_calls_from_json

FIXTURE_PATH = Path(__file__).resolve().parents[3] / "data" / "raw" / "carecall_transcripts.json"
EXTRACTOR = DeterministicTimelineExtractor()
DETECTOR = DeterministicPatternDetector()


def _events_for_patient(patient_id: str) -> List[TimelineEvent]:
    calls = [c for c in load_calls_from_json(FIXTURE_PATH) if c.patient.id == patient_id]
    events: List[TimelineEvent] = []
    for call in calls:
        events.extend(EXTRACTOR.extract(call))
    return events


def _fabricate_event(
    call_id: str, date: str, event_type: str, quote: str, turn: int = 1, patient_id: str = "P-9999",
) -> TimelineEvent:
    return TimelineEvent(
        event_id=f"evt-{call_id}-{turn}-{event_type}",
        patient_id=patient_id,
        event_type=event_type,
        title="t", description="d", observed_date=date,
        source_call_id=call_id, source_turn_start=turn, source_turn_end=turn,
        quote=quote, confidence="medium", extraction_method="deterministic",
        review_status="unreviewed", created_at=date, updated_at=date,
        dedupe_key=f"{event_type}:{turn}",
    )


def test_symptom_reported_and_recurrence_merge_into_one_repeated_pattern():
    """Margaret Chen (P-1001) has a symptom_reported event in call_009 and a
    symptom_recurrence event in call_015 - both describe the same underlying
    dizziness concern and must merge into ONE repeated_occurrence pattern,
    not a repeated pattern plus a spurious extra first_occurrence."""
    events = _events_for_patient("P-1001")
    patterns = DETECTOR.detect("P-1001", events)

    symptom_patterns = [p for p in patterns if p.pattern_type == "repeated_occurrence"]
    assert len(symptom_patterns) == 1
    assert symptom_patterns[0].related_call_ids == ("call_009", "call_015")


def test_medication_started_before_symptom_uses_non_causal_wording():
    events = _events_for_patient("P-1001")
    patterns = DETECTOR.detect("P-1001", events)
    med_patterns = [p for p in patterns if p.pattern_type == "medication_started_before_symptom"]
    assert len(med_patterns) == 1
    pattern = med_patterns[0]
    assert pattern.status == "uncertain"
    assert "temporal observation only" in pattern.summary
    assert "not a causal" in pattern.summary
    assert "caused" not in pattern.summary.lower()
    assert "confirmed" not in pattern.summary.lower()


def test_issue_resolved_links_the_correct_prior_concern():
    """Harold Okafor (P-1006): call_017 reports a missed dose, call_020
    reports it resolved via a pillbox - the pattern must link both events
    and mark status=resolved."""
    events = _events_for_patient("P-1006")
    patterns = DETECTOR.detect("P-1006", events)
    resolved = [p for p in patterns if p.pattern_type == "issue_resolved"]
    assert len(resolved) == 1
    pattern = resolved[0]
    assert pattern.status == "resolved"
    assert pattern.related_call_ids == ("call_017", "call_020")


def test_gus_fall_pattern_never_attributes_the_event_to_samuel():
    events = _events_for_patient("P-1008")
    patterns = DETECTOR.detect("P-1008", events)
    assert patterns
    for pattern in patterns:
        assert "Samuel" not in pattern.summary
        for ref in pattern.evidence:
            if ref.call_id == "call_021":
                assert "Gus" in ref.quote
                assert "Samuel" not in ref.quote


def test_recurrence_after_resolution_is_detected_for_synthetic_data():
    events = [
        _fabricate_event("call_a", "2026-01-01", "sleep_issue", "Trouble sleeping most nights."),
        _fabricate_event("call_b", "2026-01-10", "issue_resolved", "Sleeping fine now, all set."),
        _fabricate_event("call_c", "2026-01-20", "sleep_issue", "Trouble sleeping again this week."),
    ]
    patterns = DETECTOR.detect("P-9999", events)
    recurrence = [p for p in patterns if p.pattern_type == "recurrence_after_resolution"]
    assert len(recurrence) == 1
    assert recurrence[0].severity == "high_attention"
    assert recurrence[0].related_call_ids == ("call_a", "call_b", "call_c")


def test_increasing_frequency_is_detected_when_gaps_shrink():
    events = [
        _fabricate_event("call_a", "2026-01-01", "meal_concern", "Skipping meals sometimes."),
        _fabricate_event("call_b", "2026-01-20", "meal_concern", "Skipping meals sometimes."),
        _fabricate_event("call_c", "2026-01-24", "meal_concern", "Skipping meals sometimes."),
    ]
    patterns = DETECTOR.detect("P-9999", events)
    increasing = [p for p in patterns if p.pattern_type == "increasing_frequency"]
    assert len(increasing) == 1
    assert increasing[0].severity == "high_attention"


def test_worsening_wording_is_detected_when_latest_quote_has_a_new_intensifier():
    events = [
        _fabricate_event("call_a", "2026-01-01", "sleep_issue", "A little trouble sleeping."),
        _fabricate_event("call_b", "2026-02-01", "sleep_issue", "Trouble sleeping every day now, it's constant."),
    ]
    patterns = DETECTOR.detect("P-9999", events)
    worsening = [p for p in patterns if p.pattern_type == "worsening_wording"]
    assert len(worsening) == 1
    assert worsening[0].severity == "high_attention"


def test_first_occurrence_for_a_single_event():
    events = [_fabricate_event("call_a", "2026-01-01", "transportation_issue", "The van was late again.")]
    patterns = DETECTOR.detect("P-9999", events)
    assert len(patterns) == 1
    assert patterns[0].pattern_type == "first_occurrence"
    assert patterns[0].severity == "informational"


def test_administrative_event_types_never_produce_a_pattern():
    events = [
        _fabricate_event("call_a", "2026-01-01", "appointment_request", "Need help with an appointment."),
        _fabricate_event("call_b", "2026-01-05", "follow_up_promised", "I'll flag this for the nurse."),
        _fabricate_event("call_c", "2026-01-10", "assistive_device_update", "Got a new walker."),
    ]
    assert DETECTOR.detect("P-9999", events) == []


def test_no_events_produces_no_patterns():
    assert DETECTOR.detect("P-9999", []) == []
