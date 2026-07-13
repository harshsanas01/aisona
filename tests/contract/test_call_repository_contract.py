"""Same behavioral contract for every CallRepository implementation.

The in-memory case always runs. The PostgreSQL case only runs when
DATABASE_URL is set (see CONTRIBUTING.md) - PostgreSQL is never required
for unit tests or basic local development.
"""
import os

import pytest
import sqlalchemy as sa

from carecall_domain import Call, DuplicateCallError, Patient, Turn
from carecall_persistence.in_memory import InMemoryCallRepository

POSTGRES_URL = os.environ.get("DATABASE_URL")


def _sample_call(call_id: str = "call_contract_1") -> Call:
    return Call(
        call_id=call_id,
        date="2026-01-01",
        patient=Patient(id="P-9001", name="Contract Tester", age=70),
        duration_seconds=100,
        turns=[Turn(speaker="assistant", text="Hi"), Turn(speaker="participant", text="Hello back")],
    )


def _postgres_call_repo():
    from carecall_persistence.postgres import PostgresCallRepository, create_session_factory

    engine = sa.create_engine(POSTGRES_URL)
    with engine.begin() as conn:
        conn.execute(sa.text(
            "TRUNCATE transcript_chunks, transcript_turns, calls, patients RESTART IDENTITY CASCADE"
        ))
    return PostgresCallRepository(create_session_factory(POSTGRES_URL))


_FACTORIES = [pytest.param(InMemoryCallRepository, id="in_memory")]
if POSTGRES_URL:
    _FACTORIES.append(pytest.param(_postgres_call_repo, id="postgres"))


@pytest.fixture(params=_FACTORIES)
def call_repository(request):
    return request.param()


def test_add_and_get_call(call_repository):
    call = _sample_call()
    call_repository.add_call(call)
    fetched = call_repository.get_call(call.call_id)
    assert fetched is not None
    assert fetched.call_id == call.call_id
    assert fetched.patient.name == call.patient.name
    assert [t.text for t in fetched.turns] == [t.text for t in call.turns]


def test_exists_reflects_added_call(call_repository):
    assert call_repository.exists("call_contract_1") is False
    call_repository.add_call(_sample_call())
    assert call_repository.exists("call_contract_1") is True


def test_duplicate_call_id_is_rejected(call_repository):
    call_repository.add_call(_sample_call())
    with pytest.raises(DuplicateCallError):
        call_repository.add_call(_sample_call())


def test_list_calls_includes_added_call(call_repository):
    call_repository.add_call(_sample_call())
    calls = call_repository.list_calls()
    assert any(c.call_id == "call_contract_1" for c in calls)


def test_get_unknown_call_returns_none(call_repository):
    assert call_repository.get_call("does-not-exist") is None
