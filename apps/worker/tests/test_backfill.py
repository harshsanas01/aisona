import os

import pytest
import sqlalchemy as sa

POSTGRES_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(not POSTGRES_URL, reason="requires DATABASE_URL (PostgreSQL)")


def test_backfill_embeds_chunks_missing_embeddings():
    from carecall_domain import Call, Patient, Turn
    from carecall_persistence.postgres import (
        PostgresCallRepository,
        PostgresChunkRepository,
        create_session_factory,
    )
    from carecall_persistence.postgres.models import TranscriptChunkRow
    from carecall_retrieval import build_chunks

    from carecall_worker.main import backfill_embeddings_once

    engine = sa.create_engine(POSTGRES_URL)
    with engine.begin() as conn:
        conn.execute(sa.text(
            "TRUNCATE transcript_chunks, transcript_turns, calls, patients RESTART IDENTITY CASCADE"
        ))

    session_factory = create_session_factory(POSTGRES_URL)
    call_repository = PostgresCallRepository(session_factory)
    chunk_repository = PostgresChunkRepository(session_factory)

    call = Call(
        call_id="call_worker_test",
        date="2026-01-01",
        patient=Patient(id="P-WORKER", name="Worker Tester", age=70),
        duration_seconds=60,
        turns=[Turn(speaker="assistant", text="Hi"), Turn(speaker="participant", text="Hello")],
    )
    call_repository.add_call(call)
    chunk_repository.add_chunks(build_chunks(call))

    with session_factory() as session:
        pending_before = session.query(TranscriptChunkRow).filter(TranscriptChunkRow.embedding.is_(None)).count()
    assert pending_before > 0

    processed = backfill_embeddings_once(session_factory)
    assert processed == pending_before

    with session_factory() as session:
        pending_after = session.query(TranscriptChunkRow).filter(TranscriptChunkRow.embedding.is_(None)).count()
    assert pending_after == 0
