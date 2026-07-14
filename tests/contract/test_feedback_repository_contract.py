"""Same behavioral contract for every FeedbackRepository implementation.

The in-memory case always runs. The PostgreSQL case only runs when
DATABASE_URL is set (see CONTRIBUTING.md) - PostgreSQL is never required
for unit tests or basic local development.
"""
import os

import pytest
import sqlalchemy as sa

from carecall_domain import Feedback
from carecall_persistence.in_memory import InMemoryFeedbackRepository

POSTGRES_URL = os.environ.get("DATABASE_URL")


def _sample_feedback(feedback_id: str = "fb_contract_1", **overrides) -> Feedback:
    fields = dict(
        feedback_id=feedback_id,
        target_type="answer",
        target_id="req-123",
        category="incorrect",
        actor="coordinator_amy",
        created_at="2026-06-01T00:00:00+00:00",
        comment="This cited the wrong patient.",
        corrected_value=None,
        prompt_version="v1",
        retrieval_version="v1",
        model_version="mock",
    )
    fields.update(overrides)
    return Feedback(**fields)


class _MemoryFixture:
    def build(self):
        return InMemoryFeedbackRepository()


class _PostgresFixture:
    def build(self):
        from carecall_persistence.postgres import create_session_factory, PostgresFeedbackRepository

        engine = sa.create_engine(POSTGRES_URL)
        with engine.begin() as conn:
            conn.execute(sa.text("TRUNCATE feedback RESTART IDENTITY CASCADE"))
        session_factory = create_session_factory(POSTGRES_URL)
        return PostgresFeedbackRepository(session_factory)


_FACTORIES = [pytest.param(_MemoryFixture, id="in_memory")]
if POSTGRES_URL:
    _FACTORIES.append(pytest.param(_PostgresFixture, id="postgres"))


@pytest.fixture(params=_FACTORIES)
def feedback_repository(request):
    return request.param().build()


def test_create_then_get(feedback_repository):
    feedback_repository.create(_sample_feedback())
    record = feedback_repository.get("fb_contract_1")
    assert record is not None
    assert record.category == "incorrect"
    assert record.comment == "This cited the wrong patient."


def test_get_unknown_feedback_returns_none(feedback_repository):
    assert feedback_repository.get("does-not-exist") is None


def test_list_feedback_filters_by_target_type_and_category(feedback_repository):
    feedback_repository.create(_sample_feedback("fb_1", target_type="answer", category="incorrect"))
    feedback_repository.create(_sample_feedback("fb_2", target_type="timeline_event", category="confirm", target_id="evt-1"))
    feedback_repository.create(_sample_feedback("fb_3", target_type="answer", category="correct"))

    answers_only = feedback_repository.list_feedback(target_type="answer")
    assert {r.feedback_id for r in answers_only} == {"fb_1", "fb_3"}

    incorrect_only = feedback_repository.list_feedback(category="incorrect")
    assert {r.feedback_id for r in incorrect_only} == {"fb_1"}


def test_list_feedback_respects_limit(feedback_repository):
    for i in range(5):
        feedback_repository.create(_sample_feedback(f"fb_{i}"))
    assert len(feedback_repository.list_feedback(limit=2)) == 2
