"""Same behavioral contract for every BriefRepository implementation.

The in-memory case always runs. The PostgreSQL case only runs when
DATABASE_URL is set (see CONTRIBUTING.md) - PostgreSQL is never required
for unit tests or basic local development.
"""
import os
from dataclasses import replace

import pytest
import sqlalchemy as sa

from carecall_domain import Brief, BriefBullet, PatternEvidenceRef
from carecall_persistence.in_memory import InMemoryBriefRepository

POSTGRES_URL = os.environ.get("DATABASE_URL")


def _sample_bullet(bullet_id: str = "bul_1") -> BriefBullet:
    return BriefBullet(
        bullet_id=bullet_id,
        section="high_attention",
        patient_id="P-9001",
        patient_name="Contract Tester",
        summary="Observed pattern: something notable happened.",
        related_timeline_event_ids=("evt-1",),
        evidence=(PatternEvidenceRef(
            timeline_event_id="evt-1", call_id="call_contract_1", turn_start=2, turn_end=2, quote="a quote",
        ),),
        related_pattern_id="pat-1",
    )


def _sample_brief(brief_id: str = "brief_contract_1", **overrides) -> Brief:
    fields = dict(
        brief_id=brief_id,
        brief_type="daily",
        start_date="2026-06-01",
        end_date="2026-06-01",
        patient_id="P-9001",
        include_resolved=False,
        bullets=(_sample_bullet(),),
        model_version="deterministic",
        prompt_version="v1",
        generated_at="2026-06-01T00:00:00+00:00",
        created_at="2026-06-01T00:00:00+00:00",
        updated_at="2026-06-01T00:00:00+00:00",
    )
    fields.update(overrides)
    return Brief(**fields)


class _MemoryFixture:
    def build(self):
        return InMemoryBriefRepository()


class _PostgresFixture:
    def build(self):
        from carecall_persistence.postgres import create_session_factory, PostgresBriefRepository

        engine = sa.create_engine(POSTGRES_URL)
        with engine.begin() as conn:
            conn.execute(sa.text("TRUNCATE briefs RESTART IDENTITY CASCADE"))
        session_factory = create_session_factory(POSTGRES_URL)
        return PostgresBriefRepository(session_factory)


_FACTORIES = [pytest.param(_MemoryFixture, id="in_memory")]
if POSTGRES_URL:
    _FACTORIES.append(pytest.param(_PostgresFixture, id="postgres"))


@pytest.fixture(params=_FACTORIES)
def brief_repository(request):
    return request.param().build()


def test_create_then_get(brief_repository):
    brief_repository.create(_sample_brief())
    brief = brief_repository.get("brief_contract_1")
    assert brief is not None
    assert brief.brief_type == "daily"
    assert len(brief.bullets) == 1
    assert brief.bullets[0].evidence[0].quote == "a quote"


def test_get_unknown_brief_returns_none(brief_repository):
    assert brief_repository.get("does-not-exist") is None


def test_list_briefs_filters_by_type_and_patient(brief_repository):
    brief_repository.create(_sample_brief())
    brief_repository.create(_sample_brief(brief_id="brief_contract_2", brief_type="weekly", patient_id="P-9002"))

    daily = brief_repository.list_briefs(brief_type="daily")
    assert [b.brief_id for b in daily] == ["brief_contract_1"]

    for_patient = brief_repository.list_briefs(patient_id="P-9002")
    assert [b.brief_id for b in for_patient] == ["brief_contract_2"]


def test_update_persists_new_bullets_and_generated_at(brief_repository):
    brief = brief_repository.create(_sample_brief())
    updated = brief_repository.update(replace(
        brief, bullets=(_sample_bullet("bul_2"),), generated_at="2026-06-02T00:00:00+00:00",
    ))
    assert len(updated.bullets) == 1
    assert updated.bullets[0].bullet_id == "bul_2"

    fetched = brief_repository.get("brief_contract_1")
    assert fetched.bullets[0].bullet_id == "bul_2"
