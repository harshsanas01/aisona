"""Same behavioral contract for every TaskActivityRepository implementation.

The in-memory case always runs. The PostgreSQL case only runs when
DATABASE_URL is set (see CONTRIBUTING.md) - PostgreSQL is never required
for unit tests or basic local development.
"""
import os

import pytest
import sqlalchemy as sa

from carecall_domain import Call, CoordinatorTask, Patient, TaskActivity, Turn
from carecall_persistence.in_memory import InMemoryCoordinatorTaskRepository, InMemoryTaskActivityRepository

POSTGRES_URL = os.environ.get("DATABASE_URL")

_PATIENT = Patient(id="P-9002", name="Activity Tester", age=68)
_CALL = Call(
    call_id="call_contract_activity_1",
    date="2026-01-01",
    patient=_PATIENT,
    duration_seconds=60,
    turns=[Turn(speaker="participant", text="Hello")],
)
_TASK = CoordinatorTask(
    task_id="task_activity_contract_1",
    title="Follow up",
    description="d",
    patient_id=_PATIENT.id,
    priority="normal",
    status="open",
    category="general_outreach",
    is_suggested=False,
    created_by="coordinator_amy",
    created_at="2026-01-01T00:00:00+00:00",
    updated_at="2026-01-01T00:00:00+00:00",
)


def _sample_activity(activity_id: str = "act_contract_1", **overrides) -> TaskActivity:
    fields = dict(
        activity_id=activity_id,
        task_id=_TASK.task_id,
        action="created",
        actor="coordinator_amy",
        created_at="2026-01-01T00:00:00+00:00",
        from_status=None,
        to_status="open",
        note=None,
    )
    fields.update(overrides)
    return TaskActivity(**fields)


class _MemoryFixture:
    def build(self):
        InMemoryCoordinatorTaskRepository().create(_TASK)
        return InMemoryTaskActivityRepository()


class _PostgresFixture:
    def build(self):
        from carecall_persistence.postgres import (
            PostgresCallRepository,
            PostgresCoordinatorTaskRepository,
            PostgresTaskActivityRepository,
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
        PostgresCoordinatorTaskRepository(session_factory).create(_TASK)
        return PostgresTaskActivityRepository(session_factory)


_FACTORIES = [pytest.param(_MemoryFixture, id="in_memory")]
if POSTGRES_URL:
    _FACTORIES.append(pytest.param(_PostgresFixture, id="postgres"))


@pytest.fixture(params=_FACTORIES)
def activity_repository(request):
    return request.param().build()


def test_add_then_list_for_task(activity_repository):
    activity_repository.add(_sample_activity())
    activities = activity_repository.list_for_task(_TASK.task_id)
    assert len(activities) == 1
    assert activities[0].action == "created"
    assert activities[0].to_status == "open"


def test_list_for_unknown_task_returns_empty(activity_repository):
    assert activity_repository.list_for_task("does-not-exist") == []


def test_activities_are_appended_in_order(activity_repository):
    activity_repository.add(_sample_activity("act_1", action="created", to_status="open"))
    activity_repository.add(_sample_activity(
        "act_2", action="status_changed", from_status="open", to_status="in_progress",
    ))
    activities = activity_repository.list_for_task(_TASK.task_id)
    assert [a.activity_id for a in activities] == ["act_1", "act_2"]
    assert activities[1].from_status == "open"
    assert activities[1].to_status == "in_progress"
