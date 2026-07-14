"""Same behavioral contract for every PatternRepository implementation.

The in-memory case always runs. The PostgreSQL case only runs when
DATABASE_URL is set (see CONTRIBUTING.md) - PostgreSQL is never required
for unit tests or basic local development.
"""
import os

import pytest
import sqlalchemy as sa

from carecall_domain import Call, Patient, PatientPattern, PatternEvidenceRef, Turn
from carecall_persistence.in_memory import InMemoryPatternRepository

POSTGRES_URL = os.environ.get("DATABASE_URL")

_PATIENT = Patient(id="P-9001", name="Contract Tester", age=70)
_CALL = Call(
    call_id="call_contract_pattern_1",
    date="2026-01-01",
    patient=_PATIENT,
    duration_seconds=100,
    turns=[Turn(speaker="assistant", text="Hi"), Turn(speaker="participant", text="Trouble sleeping again")],
)


def _sample_pattern(pattern_id: str = "pat_contract_1", dedupe_key: str = "dedupe-1", **overrides) -> PatientPattern:
    fields = dict(
        pattern_id=pattern_id,
        patient_id=_PATIENT.id,
        pattern_type="repeated_occurrence",
        title="Repeated: a sleep issue (2 occurrences)",
        summary="Observed pattern: a sleep issue was reported 2 times. Requires staff review.",
        status="active",
        severity="attention",
        first_observed_date="2026-01-01",
        latest_observed_date="2026-01-10",
        related_timeline_event_ids=("evt-1", "evt-2"),
        related_call_ids=(_CALL.call_id,),
        evidence=(
            PatternEvidenceRef(
                timeline_event_id="evt-1", call_id=_CALL.call_id, turn_start=2, turn_end=2,
                quote="Trouble sleeping again",
            ),
        ),
        detector_version="v1",
        reviewed_status="unreviewed",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        dedupe_key=dedupe_key,
    )
    fields.update(overrides)
    return PatientPattern(**fields)


class _MemoryFixture:
    def build(self):
        return InMemoryPatternRepository()


class _PostgresFixture:
    def build(self):
        from carecall_persistence.postgres import (
            PostgresCallRepository,
            PostgresPatternRepository,
            create_session_factory,
        )

        engine = sa.create_engine(POSTGRES_URL)
        with engine.begin() as conn:
            conn.execute(sa.text(
                "TRUNCATE patient_patterns, timeline_events, transcript_chunks, transcript_turns, "
                "calls, patients RESTART IDENTITY CASCADE"
            ))
        session_factory = create_session_factory(POSTGRES_URL)
        PostgresCallRepository(session_factory).add_call(_CALL)
        return PostgresPatternRepository(session_factory)


_FACTORIES = [pytest.param(_MemoryFixture, id="in_memory")]
if POSTGRES_URL:
    _FACTORIES.append(pytest.param(_PostgresFixture, id="postgres"))


@pytest.fixture(params=_FACTORIES)
def pattern_repository(request):
    return request.param().build()


def test_upsert_then_list_for_patient(pattern_repository):
    pattern_repository.upsert_many([_sample_pattern()])
    patterns = pattern_repository.list_for_patient(_PATIENT.id)
    assert len(patterns) == 1
    assert patterns[0].pattern_id == "pat_contract_1"
    assert patterns[0].evidence[0].quote == "Trouble sleeping again"
    assert patterns[0].reviewed_status == "unreviewed"


def test_get_unknown_pattern_returns_none(pattern_repository):
    assert pattern_repository.get("does-not-exist") is None


def test_list_for_unknown_patient_returns_empty(pattern_repository):
    pattern_repository.upsert_many([_sample_pattern()])
    assert pattern_repository.list_for_patient("no-such-patient") == []


def test_upsert_is_idempotent_on_dedupe_key(pattern_repository):
    pattern_repository.upsert_many([_sample_pattern()])
    pattern_repository.upsert_many([_sample_pattern(title="Repeated: a sleep issue (3 occurrences)")])

    patterns = pattern_repository.list_for_patient(_PATIENT.id)
    assert len(patterns) == 1
    assert patterns[0].title == "Repeated: a sleep issue (3 occurrences)"


def test_reviewed_pattern_is_not_overwritten_by_rebuild(pattern_repository):
    pattern_repository.upsert_many([_sample_pattern()])
    pattern_repository.update_reviewed_status("pat_contract_1", "confirmed")

    pattern_repository.upsert_many([_sample_pattern(title="Different re-detected title")])

    patterns = pattern_repository.list_for_patient(_PATIENT.id)
    assert len(patterns) == 1
    assert patterns[0].reviewed_status == "confirmed"
    assert patterns[0].title == "Repeated: a sleep issue (2 occurrences)"  # unchanged by the rebuild


def test_update_reviewed_status_returns_updated_pattern(pattern_repository):
    pattern_repository.upsert_many([_sample_pattern()])
    updated = pattern_repository.update_reviewed_status("pat_contract_1", "dismissed")
    assert updated is not None
    assert updated.reviewed_status == "dismissed"


def test_update_reviewed_status_for_unknown_pattern_returns_none(pattern_repository):
    assert pattern_repository.update_reviewed_status("does-not-exist", "confirmed") is None


def test_distinct_dedupe_keys_do_not_collide(pattern_repository):
    pattern_repository.upsert_many([
        _sample_pattern(pattern_id="pat_a", dedupe_key="dedupe-a"),
        _sample_pattern(pattern_id="pat_b", dedupe_key="dedupe-b"),
    ])
    patterns = pattern_repository.list_for_patient(_PATIENT.id)
    assert {p.pattern_id for p in patterns} == {"pat_a", "pat_b"}
