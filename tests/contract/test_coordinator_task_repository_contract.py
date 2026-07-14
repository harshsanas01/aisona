"""Same behavioral contract for every CoordinatorTaskRepository
implementation.

The in-memory case always runs. The PostgreSQL case only runs when
DATABASE_URL is set (see CONTRIBUTING.md) - PostgreSQL is never required
for unit tests or basic local development.
"""
import os
from dataclasses import replace

import pytest
import sqlalchemy as sa

from carecall_domain import Call, CoordinatorTask, Patient, Turn
from carecall_persistence.in_memory import InMemoryCoordinatorTaskRepository

POSTGRES_URL = os.environ.get("DATABASE_URL")

_PATIENT = Patient(id="P-9001", name="Contract Tester", age=70)
_CALL = Call(
    call_id="call_contract_task_1",
    date="2026-01-01",
    patient=_PATIENT,
    duration_seconds=100,
    turns=[Turn(speaker="assistant", text="Hi"), Turn(speaker="participant", text="The van was late again")],
)


def _sample_task(task_id: str = "task_contract_1", **overrides) -> CoordinatorTask:
    fields = dict(
        task_id=task_id,
        title="Follow up: transportation issue",
        description="Coordinator follow-up suggested based on an observed transcript event.",
        patient_id=_PATIENT.id,
        priority="normal",
        status="open",
        category="transportation",
        is_suggested=True,
        created_by="system",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        source_event_id="evt-1",
        source_call_id=_CALL.call_id,
        source_turn_start=2,
        source_turn_end=2,
        dedupe_key="suggested:evt-1",
    )
    fields.update(overrides)
    return CoordinatorTask(**fields)


class _MemoryFixture:
    def build(self):
        return InMemoryCoordinatorTaskRepository()


class _PostgresFixture:
    def build(self):
        from carecall_persistence.postgres import (
            PostgresCallRepository,
            PostgresCoordinatorTaskRepository,
            create_session_factory,
        )

        engine = sa.create_engine(POSTGRES_URL)
        with engine.begin() as conn:
            conn.execute(sa.text(
                "TRUNCATE task_activity, coordinator_tasks, patient_patterns, timeline_events, "
                "transcript_chunks, transcript_turns, calls, patients RESTART IDENTITY CASCADE"
            ))
        session_factory = create_session_factory(POSTGRES_URL)
        PostgresCallRepository(session_factory).add_call(_CALL)
        return PostgresCoordinatorTaskRepository(session_factory)


_FACTORIES = [pytest.param(_MemoryFixture, id="in_memory")]
if POSTGRES_URL:
    _FACTORIES.append(pytest.param(_PostgresFixture, id="postgres"))


@pytest.fixture(params=_FACTORIES)
def task_repository(request):
    return request.param().build()


def test_create_then_get(task_repository):
    task_repository.create(_sample_task())
    task = task_repository.get("task_contract_1")
    assert task is not None
    assert task.title == "Follow up: transportation issue"
    assert task.is_suggested is True
    assert task.status == "open"


def test_get_unknown_task_returns_none(task_repository):
    assert task_repository.get("does-not-exist") is None


def test_list_tasks_filters_by_status_and_patient(task_repository):
    task_repository.create(_sample_task())
    task_repository.create(_sample_task(task_id="task_contract_2", status="completed", dedupe_key="other-key"))

    open_tasks = task_repository.list_tasks(patient_id=_PATIENT.id, status="open")
    assert [t.task_id for t in open_tasks] == ["task_contract_1"]

    all_tasks = task_repository.list_tasks(patient_id=_PATIENT.id)
    assert len(all_tasks) == 2


def test_find_by_dedupe_key(task_repository):
    task_repository.create(_sample_task())
    found = task_repository.find_by_dedupe_key(_PATIENT.id, "suggested:evt-1")
    assert found is not None
    assert found.task_id == "task_contract_1"
    assert task_repository.find_by_dedupe_key(_PATIENT.id, "no-such-key") is None


def test_update_persists_changes(task_repository):
    task = task_repository.create(_sample_task())
    updated = task_repository.update(replace(task, status="in_progress", assignee="Nurse Amy"))
    assert updated.status == "in_progress"
    assert updated.assignee == "Nurse Amy"

    fetched = task_repository.get("task_contract_1")
    assert fetched.status == "in_progress"
    assert fetched.assignee == "Nurse Amy"
