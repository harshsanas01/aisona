"""Same behavioral contract for every TimelineEventRepository implementation.

The in-memory case always runs. The PostgreSQL case only runs when
DATABASE_URL is set (see CONTRIBUTING.md) - PostgreSQL is never required
for unit tests or basic local development.
"""
import os

import pytest
import sqlalchemy as sa

from carecall_domain import Call, Patient, TimelineEvent, Turn
from carecall_persistence.in_memory import (
    InMemoryCallRepository,
    InMemoryPatientRepository,
    InMemoryTimelineEventRepository,
)

POSTGRES_URL = os.environ.get("DATABASE_URL")

_PATIENT = Patient(id="P-9001", name="Contract Tester", age=70)
_CALL = Call(
    call_id="call_contract_timeline_1",
    date="2026-01-01",
    patient=_PATIENT,
    duration_seconds=100,
    turns=[Turn(speaker="assistant", text="Hi"), Turn(speaker="participant", text="I've been dizzy")],
)


def _sample_event(event_id: str = "evt_contract_1", dedupe_key: str = "dedupe-1", **overrides) -> TimelineEvent:
    fields = dict(
        event_id=event_id,
        patient_id=_PATIENT.id,
        event_type="symptom_reported",
        title="Dizziness reported",
        description="Participant reported feeling dizzy.",
        observed_date=_CALL.date,
        source_call_id=_CALL.call_id,
        source_turn_start=2,
        source_turn_end=2,
        quote="I've been dizzy",
        confidence="medium",
        extraction_method="deterministic",
        review_status="unreviewed",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        dedupe_key=dedupe_key,
    )
    fields.update(overrides)
    return TimelineEvent(**fields)


class _MemoryFixture:
    def build(self):
        call_repository = InMemoryCallRepository([_CALL])
        InMemoryPatientRepository(call_repository)
        return InMemoryTimelineEventRepository()


class _PostgresFixture:
    def build(self):
        from carecall_persistence.postgres import PostgresTimelineEventRepository, create_session_factory

        engine = sa.create_engine(POSTGRES_URL)
        with engine.begin() as conn:
            conn.execute(sa.text(
                "TRUNCATE timeline_events, transcript_chunks, transcript_turns, calls, patients RESTART IDENTITY CASCADE"
            ))
        session_factory = create_session_factory(POSTGRES_URL)

        from carecall_persistence.postgres import PostgresCallRepository

        PostgresCallRepository(session_factory).add_call(_CALL)
        return PostgresTimelineEventRepository(session_factory)


_FACTORIES = [pytest.param(_MemoryFixture, id="in_memory")]
if POSTGRES_URL:
    _FACTORIES.append(pytest.param(_PostgresFixture, id="postgres"))


@pytest.fixture(params=_FACTORIES)
def timeline_repository(request):
    return request.param().build()


def test_upsert_then_list_for_patient(timeline_repository):
    timeline_repository.upsert_many([_sample_event()])
    events = timeline_repository.list_for_patient(_PATIENT.id)
    assert len(events) == 1
    assert events[0].event_id == "evt_contract_1"
    assert events[0].quote == "I've been dizzy"
    assert events[0].review_status == "unreviewed"


def test_get_unknown_event_returns_none(timeline_repository):
    assert timeline_repository.get("does-not-exist") is None


def test_list_for_unknown_patient_returns_empty(timeline_repository):
    timeline_repository.upsert_many([_sample_event()])
    assert timeline_repository.list_for_patient("no-such-patient") == []


def test_upsert_is_idempotent_on_dedupe_key(timeline_repository):
    """Re-running extraction over the same chunk must not create a
    duplicate event - this is what makes reprocessing idempotent."""
    timeline_repository.upsert_many([_sample_event()])
    timeline_repository.upsert_many([_sample_event(title="Dizziness reported (re-extracted)")])

    events = timeline_repository.list_for_patient(_PATIENT.id)
    assert len(events) == 1
    assert events[0].title == "Dizziness reported (re-extracted)"


def test_reviewed_event_is_not_overwritten_by_rebuild(timeline_repository):
    """A coordinator's review decision must survive a re-extraction rebuild
    of the same call - otherwise every rebuild would silently discard human
    review work."""
    timeline_repository.upsert_many([_sample_event()])
    timeline_repository.update_review_status("evt_contract_1", "confirmed")

    timeline_repository.upsert_many([_sample_event(title="Different re-extracted title")])

    events = timeline_repository.list_for_patient(_PATIENT.id)
    assert len(events) == 1
    assert events[0].review_status == "confirmed"
    assert events[0].title == "Dizziness reported"  # unchanged by the rebuild


def test_update_review_status_returns_updated_event(timeline_repository):
    timeline_repository.upsert_many([_sample_event()])
    updated = timeline_repository.update_review_status(
        "evt_contract_1", "corrected", title="Corrected title", description="Corrected description",
    )
    assert updated is not None
    assert updated.review_status == "corrected"
    assert updated.title == "Corrected title"
    assert updated.description == "Corrected description"


def test_update_review_status_for_unknown_event_returns_none(timeline_repository):
    assert timeline_repository.update_review_status("does-not-exist", "dismissed") is None


def test_distinct_dedupe_keys_do_not_collide(timeline_repository):
    timeline_repository.upsert_many([
        _sample_event(event_id="evt_a", dedupe_key="dedupe-a"),
        _sample_event(event_id="evt_b", dedupe_key="dedupe-b"),
    ])
    events = timeline_repository.list_for_patient(_PATIENT.id)
    assert {e.event_id for e in events} == {"evt_a", "evt_b"}
