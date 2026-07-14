from pathlib import Path

from carecall_domain import Call, DeterministicTimelineExtractor, Patient, Turn
from carecall_persistence.in_memory.loader import load_calls_from_json

FIXTURE_PATH = Path(__file__).resolve().parents[3] / "data" / "raw" / "carecall_transcripts.json"
EXTRACTOR = DeterministicTimelineExtractor()


def _call_by_id(call_id: str) -> Call:
    calls = load_calls_from_json(FIXTURE_PATH)
    return next(c for c in calls if c.call_id == call_id)


def test_medication_started_is_extracted_with_verbatim_quote():
    call = _call_by_id("call_003")
    events = EXTRACTOR.extract(call)
    started = [e for e in events if e.event_type == "medication_started"]
    assert len(started) == 1
    event = started[0]
    assert event.source_call_id == "call_003"
    assert event.source_turn_start == 4
    assert event.source_turn_end == 4
    assert "lisinopril" in event.quote.lower()
    assert event.review_status == "unreviewed"
    assert event.extraction_method == "deterministic"


def test_musing_about_an_existing_pill_is_not_a_new_medication_started_event():
    """call_015 turn 6 has Margaret wondering aloud whether "the new pill"
    (already started back in call_003) might be behind her dizziness - this
    must not be read as a second, incorrect medication_started event."""
    call = _call_by_id("call_015")
    events = EXTRACTOR.extract(call)
    assert not any(e.event_type == "medication_started" for e in events)


def test_symptom_recurrence_detected_when_turn_says_it_happened_again():
    call = _call_by_id("call_015")
    events = EXTRACTOR.extract(call)
    recurrence = [e for e in events if e.event_type == "symptom_recurrence"]
    assert len(recurrence) == 1
    assert recurrence[0].source_turn_start == 2
    assert "again" in recurrence[0].quote.lower()


def test_missed_medication_maps_to_medication_adherence_concern():
    call = _call_by_id("call_017")
    events = EXTRACTOR.extract(call)
    concern = [e for e in events if e.event_type == "medication_adherence_concern"]
    assert len(concern) == 1
    assert "didn't take any" in concern[0].quote.lower()


def test_resolution_is_extracted_as_issue_resolved():
    call = _call_by_id("call_020")
    events = EXTRACTOR.extract(call)
    resolved = [e for e in events if e.event_type == "issue_resolved"]
    assert len(resolved) == 1
    assert resolved[0].source_turn_start == 6


def test_staff_commitment_is_extracted_only_from_assistant_turns():
    call = _call_by_id("call_004")
    events = EXTRACTOR.extract(call)
    promised = [e for e in events if e.event_type == "follow_up_promised"]
    assert promised
    assert all(call.turns[e.source_turn_start - 1].speaker == "assistant" for e in promised)


def test_gus_fall_is_extracted_without_attributing_it_to_samuel():
    call = _call_by_id("call_021")
    assert call.patient.name == "Samuel Rivera"
    events = EXTRACTOR.extract(call)
    home_safety = [e for e in events if e.event_type == "home_safety_concern"]
    assert home_safety
    for event in home_safety:
        assert "Gus" in event.quote
        assert "Samuel" not in event.quote
    assert all(e.patient_id == call.patient.id for e in home_safety)


def test_assistant_turns_never_produce_safety_derived_categories():
    """Only the participant's own words are evidence for symptom/medication/
    home-safety/etc. categories - mirrors DeterministicSafetyClassifier's
    same guarantee, since this extractor reuses it directly."""
    call = Call(
        call_id="call_synthetic_1",
        date="2026-01-01",
        patient=Patient(id="P-9999", name="Synthetic Patient", age=80),
        duration_seconds=60,
        turns=[
            Turn(speaker="assistant", text="Any dizziness, falls, or missed medications since we last spoke?"),
            Turn(speaker="participant", text="No, none of that this week."),
        ],
    )
    events = EXTRACTOR.extract(call)
    assert events == []


def test_reprocessing_the_same_call_produces_identical_dedupe_keys():
    """Idempotent reprocessing: re-running extraction over an unchanged call
    must produce the same dedupe_key for the same underlying event so the
    repository's upsert never creates a duplicate."""
    call = _call_by_id("call_015")
    first_run = {e.dedupe_key: e.event_type for e in EXTRACTOR.extract(call)}
    second_run = {e.dedupe_key: e.event_type for e in EXTRACTOR.extract(call)}
    assert first_run == second_run
    assert len(first_run) == len(set(first_run))


def test_no_event_is_produced_for_a_call_with_no_matching_language():
    call = Call(
        call_id="call_synthetic_2",
        date="2026-01-01",
        patient=Patient(id="P-9998", name="Quiet Patient", age=75),
        duration_seconds=60,
        turns=[
            Turn(speaker="assistant", text="Good morning! How are you today?"),
            Turn(speaker="participant", text="Just fine, thank you. Nothing new to report."),
        ],
    )
    assert EXTRACTOR.extract(call) == []
