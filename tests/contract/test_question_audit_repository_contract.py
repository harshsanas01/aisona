"""Same behavioral contract for every QuestionAuditRepository
implementation.

The in-memory case always runs. The PostgreSQL case only runs when
DATABASE_URL is set (see CONTRIBUTING.md) - PostgreSQL is never required
for unit tests or basic local development.
"""
import os

import pytest
import sqlalchemy as sa

from carecall_domain import QuestionAudit
from carecall_persistence.in_memory import InMemoryQuestionAuditRepository

POSTGRES_URL = os.environ.get("DATABASE_URL")


def _sample_record(request_id: str = "req_contract_1", **overrides) -> QuestionAudit:
    fields = dict(
        request_id=request_id,
        created_at="2026-06-01T00:00:00+00:00",
        question_hash="abc123",
        filters={"patient_id": None, "start_date": None, "end_date": None},
        storage_mode="memory",
        retrieval_mode="hybrid",
        lexical_weight=0.45,
        semantic_weight=0.55,
        top_k=8,
        relevance_threshold=0.15,
        candidate_chunk_ids=("call_001:1:2",),
        selected_evidence_ids=("call_001:1:2",),
        answer_mode="mock",
        provider="mock",
        prompt_version="v1",
        latency_ms=12.5,
        answerable=True,
        confidence="high",
        final_citation_call_ids=("call_001",),
        grounding_checks={"answerability_gate": True},
        fallback_used=False,
    )
    fields.update(overrides)
    return QuestionAudit(**fields)


class _MemoryFixture:
    def build(self):
        return InMemoryQuestionAuditRepository()


class _PostgresFixture:
    def build(self):
        from carecall_persistence.postgres import create_session_factory, PostgresQuestionAuditRepository

        engine = sa.create_engine(POSTGRES_URL)
        with engine.begin() as conn:
            conn.execute(sa.text("TRUNCATE question_audit RESTART IDENTITY CASCADE"))
        session_factory = create_session_factory(POSTGRES_URL)
        return PostgresQuestionAuditRepository(session_factory)


_FACTORIES = [pytest.param(_MemoryFixture, id="in_memory")]
if POSTGRES_URL:
    _FACTORIES.append(pytest.param(_PostgresFixture, id="postgres"))


@pytest.fixture(params=_FACTORIES)
def audit_repository(request):
    return request.param().build()


def test_create_then_get(audit_repository):
    audit_repository.create(_sample_record())
    record = audit_repository.get("req_contract_1")
    assert record is not None
    assert record.question_hash == "abc123"
    assert record.answerable is True
    assert record.question_preview is None


def test_get_unknown_request_returns_none(audit_repository):
    assert audit_repository.get("does-not-exist") is None


def test_list_records_filters_by_answerable_and_respects_limit(audit_repository):
    audit_repository.create(_sample_record("req_1", answerable=True))
    audit_repository.create(_sample_record("req_2", answerable=False))
    audit_repository.create(_sample_record("req_3", answerable=True))

    answerable_only = audit_repository.list_records(answerable=True)
    assert {r.request_id for r in answerable_only} == {"req_1", "req_3"}

    limited = audit_repository.list_records(limit=1)
    assert len(limited) == 1


def test_question_preview_is_none_unless_explicitly_set(audit_repository):
    audit_repository.create(_sample_record("req_preview", question_preview="what medication…"))
    record = audit_repository.get("req_preview")
    assert record.question_preview == "what medication…"
