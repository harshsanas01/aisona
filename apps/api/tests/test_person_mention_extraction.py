from pathlib import Path

from carecall_domain import Call, DeterministicPersonMentionExtractor, Patient, Turn
from carecall_persistence.in_memory.loader import load_calls_from_json

FIXTURE_PATH = Path(__file__).resolve().parents[3] / "data" / "raw" / "carecall_transcripts.json"
EXTRACTOR = DeterministicPersonMentionExtractor()


def _call_by_id(call_id: str) -> Call:
    calls = load_calls_from_json(FIXTURE_PATH)
    return next(c for c in calls if c.call_id == call_id)


def test_gus_next_door_is_extracted_as_a_neighbor_never_family_or_participant():
    """call_021: Samuel says "poor Gus next door had a rough weekend" -
    Gus must be tagged as Samuel's neighbor, never as family (which would
    wrongly imply a closer relationship) or participant (which would wrongly
    imply Gus is enrolled in the CareCall program)."""
    call = _call_by_id("call_021")
    assert call.patient.name == "Samuel Rivera"
    mentions = EXTRACTOR.extract(call)

    neighbor_mentions = [m for m in mentions if m.mentioned_name == "Gus"]
    assert neighbor_mentions
    for mention in neighbor_mentions:
        assert mention.relationship_type == "neighbor"
        assert mention.patient_id == call.patient.id
        assert mention.source_call_id == "call_021"


def test_gus_son_is_extracted_as_unknown_never_attributed_to_samuel():
    """call_021 turn 3: "His son drove him to urgent care" refers to Gus's
    son, not Samuel's. The extractor cannot resolve the pronoun, so this
    must be typed "unknown" - never "family" (which would falsely claim
    Samuel has a son) and never carry Samuel's name as the implied owner."""
    call = _call_by_id("call_021")
    mentions = EXTRACTOR.extract(call)

    son_mentions = [m for m in mentions if m.role_label == "son"]
    assert son_mentions
    for mention in son_mentions:
        assert mention.relationship_type == "unknown"
        assert mention.mentioned_name is None
        assert "Samuel" not in (mention.mentioned_name or "")


def test_my_daughter_with_name_is_extracted_as_family():
    call = _call_by_id("call_002")
    mentions = EXTRACTOR.extract(call)
    family = [m for m in mentions if m.relationship_type == "family"]
    assert any(m.role_label == "daughter" and m.mentioned_name == "Maria" for m in family)


def test_my_granddaughter_with_name_is_extracted_as_family():
    call = _call_by_id("call_006")
    mentions = EXTRACTOR.extract(call)
    family = [m for m in mentions if m.relationship_type == "family"]
    assert any(m.role_label == "granddaughter" and m.mentioned_name == "Lily" for m in family)


def test_nurse_mentions_are_extracted_as_staff_from_either_speaker():
    call = _call_by_id("call_009")
    mentions = EXTRACTOR.extract(call)
    staff = [m for m in mentions if m.relationship_type == "staff" and m.role_label == "nurse"]
    assert staff
    speakers = {call.turns[m.source_turn - 1].speaker for m in staff}
    assert "assistant" in speakers


def test_doctor_name_is_extracted_as_staff():
    call = _call_by_id("call_009")
    mentions = EXTRACTOR.extract(call)
    doctors = [m for m in mentions if m.relationship_type == "staff" and m.role_label == "doctor"]
    assert any(m.mentioned_name == "Patel" for m in doctors)


def test_assistant_saying_my_x_is_never_extracted_as_family():
    """"my X" possessive rules only apply to the participant's own words -
    the assistant has no personal relations relevant to the patient."""
    call = Call(
        call_id="call_synthetic_family",
        date="2026-01-01",
        patient=Patient(id="P-9997", name="Test Patient", age=70),
        duration_seconds=60,
        turns=[
            Turn(speaker="assistant", text="My daughter Jane says hello too!"),
            Turn(speaker="participant", text="That's nice."),
        ],
    )
    mentions = EXTRACTOR.extract(call)
    assert mentions == []


def test_no_mention_is_produced_for_a_call_with_no_matching_language():
    call = Call(
        call_id="call_synthetic_quiet",
        date="2026-01-01",
        patient=Patient(id="P-9998", name="Quiet Patient", age=75),
        duration_seconds=60,
        turns=[
            Turn(speaker="assistant", text="Good morning! How are you today?"),
            Turn(speaker="participant", text="Just fine, thank you. Nothing new to report."),
        ],
    )
    assert EXTRACTOR.extract(call) == []


def test_reprocessing_the_same_call_produces_identical_dedupe_keys():
    call = _call_by_id("call_021")
    first_run = {m.dedupe_key: m.relationship_type for m in EXTRACTOR.extract(call)}
    second_run = {m.dedupe_key: m.relationship_type for m in EXTRACTOR.extract(call)}
    assert first_run == second_run
    assert len(first_run) == len(set(first_run))


def test_family_mention_with_no_name_does_not_capture_the_following_verb_as_a_name():
    """call_008 turn 6: "My son said he could put some in." - the extractor
    must not mistake the lowercase verb "said" for a capitalized name. This
    guards a real bug where a plain re.IGNORECASE on the whole pattern made
    the [A-Z] name-capture group match any letter, not just proper nouns."""
    call = _call_by_id("call_008")
    mentions = EXTRACTOR.extract(call)
    sons = [m for m in mentions if m.role_label == "son"]
    assert sons
    assert all(m.mentioned_name is None for m in sons)


def test_participant_relationship_type_is_never_auto_assigned():
    """"participant" (another CareCall program participant) can only be set
    by a human coordinator's correction - the extractor cannot safely infer
    it from transcript text alone."""
    calls = load_calls_from_json(FIXTURE_PATH)
    for call in calls:
        mentions = EXTRACTOR.extract(call)
        assert all(m.relationship_type != "participant" for m in mentions)
