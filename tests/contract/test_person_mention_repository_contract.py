"""Same behavioral contract for every PersonMentionRepository implementation.

The in-memory case always runs. The PostgreSQL case only runs when
DATABASE_URL is set (see CONTRIBUTING.md) - PostgreSQL is never required
for unit tests or basic local development.
"""
import os

import pytest
import sqlalchemy as sa

from carecall_domain import Call, Patient, PersonMention, Turn
from carecall_persistence.in_memory import InMemoryPersonMentionRepository

POSTGRES_URL = os.environ.get("DATABASE_URL")

_PATIENT = Patient(id="P-9002", name="Contract Tester", age=70)
_CALL = Call(
    call_id="call_contract_person_mention_1",
    date="2026-01-01",
    patient=_PATIENT,
    duration_seconds=100,
    turns=[Turn(speaker="assistant", text="Hi"), Turn(speaker="participant", text="My neighbor Gus fell.")],
)


def _sample_mention(mention_id: str = "pm_contract_1", dedupe_key: str = "dedupe-1", **overrides) -> PersonMention:
    fields = dict(
        mention_id=mention_id,
        patient_id=_PATIENT.id,
        source_call_id=_CALL.call_id,
        source_turn=2,
        quote="My neighbor Gus fell.",
        role_label="neighbor",
        relationship_type="neighbor",
        mentioned_name="Gus",
        confidence="medium",
        extraction_method="deterministic",
        review_status="unreviewed",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        dedupe_key=dedupe_key,
    )
    fields.update(overrides)
    return PersonMention(**fields)


class _MemoryFixture:
    def build(self):
        return InMemoryPersonMentionRepository()


class _PostgresFixture:
    def build(self):
        from carecall_persistence.postgres import (
            PostgresCallRepository,
            PostgresPersonMentionRepository,
            create_session_factory,
        )

        engine = sa.create_engine(POSTGRES_URL)
        with engine.begin() as conn:
            conn.execute(sa.text(
                "TRUNCATE person_mentions, transcript_chunks, transcript_turns, calls, patients RESTART IDENTITY CASCADE"
            ))
        session_factory = create_session_factory(POSTGRES_URL)
        PostgresCallRepository(session_factory).add_call(_CALL)
        return PostgresPersonMentionRepository(session_factory)


_FACTORIES = [pytest.param(_MemoryFixture, id="in_memory")]
if POSTGRES_URL:
    _FACTORIES.append(pytest.param(_PostgresFixture, id="postgres"))


@pytest.fixture(params=_FACTORIES)
def person_mention_repository(request):
    return request.param().build()


def test_upsert_then_list_for_patient(person_mention_repository):
    person_mention_repository.upsert_many([_sample_mention()])
    mentions = person_mention_repository.list_for_patient(_PATIENT.id)
    assert len(mentions) == 1
    assert mentions[0].mention_id == "pm_contract_1"
    assert mentions[0].mentioned_name == "Gus"
    assert mentions[0].relationship_type == "neighbor"
    assert mentions[0].review_status == "unreviewed"


def test_get_unknown_mention_returns_none(person_mention_repository):
    assert person_mention_repository.get("does-not-exist") is None


def test_list_for_unknown_patient_returns_empty(person_mention_repository):
    person_mention_repository.upsert_many([_sample_mention()])
    assert person_mention_repository.list_for_patient("no-such-patient") == []


def test_upsert_is_idempotent_on_dedupe_key(person_mention_repository):
    person_mention_repository.upsert_many([_sample_mention()])
    person_mention_repository.upsert_many([_sample_mention(role_label="neighbor (re-extracted)")])

    mentions = person_mention_repository.list_for_patient(_PATIENT.id)
    assert len(mentions) == 1
    assert mentions[0].role_label == "neighbor (re-extracted)"


def test_reviewed_mention_is_not_overwritten_by_rebuild(person_mention_repository):
    person_mention_repository.upsert_many([_sample_mention()])
    person_mention_repository.update_review_status("pm_contract_1", "confirmed")

    person_mention_repository.upsert_many([_sample_mention(role_label="different role")])

    mentions = person_mention_repository.list_for_patient(_PATIENT.id)
    assert len(mentions) == 1
    assert mentions[0].review_status == "confirmed"
    assert mentions[0].role_label == "neighbor"  # unchanged by the rebuild


def test_update_review_status_returns_updated_mention(person_mention_repository):
    person_mention_repository.upsert_many([_sample_mention()])
    updated = person_mention_repository.update_review_status("pm_contract_1", "confirmed")
    assert updated is not None
    assert updated.review_status == "confirmed"


def test_update_review_status_can_correct_relationship_type_and_name(person_mention_repository):
    """The path by which a coordinator promotes a mention to "participant" -
    the extractor itself never assigns that relationship_type."""
    person_mention_repository.upsert_many([_sample_mention(relationship_type="unknown", mentioned_name=None)])
    updated = person_mention_repository.update_review_status(
        "pm_contract_1", "corrected", corrected_relationship_type="participant", corrected_name="Frank Delgado",
    )
    assert updated is not None
    assert updated.relationship_type == "participant"
    assert updated.mentioned_name == "Frank Delgado"


def test_update_review_status_for_unknown_mention_returns_none(person_mention_repository):
    assert person_mention_repository.update_review_status("does-not-exist", "dismissed") is None


def test_distinct_dedupe_keys_do_not_collide(person_mention_repository):
    person_mention_repository.upsert_many([
        _sample_mention(mention_id="pm_a", dedupe_key="dedupe-a"),
        _sample_mention(mention_id="pm_b", dedupe_key="dedupe-b"),
    ])
    mentions = person_mention_repository.list_for_patient(_PATIENT.id)
    assert {m.mention_id for m in mentions} == {"pm_a", "pm_b"}
