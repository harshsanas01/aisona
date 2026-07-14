import os
import time

from carecall_persistence.postgres import create_session_factory
from carecall_persistence.postgres.models import TranscriptChunkRow
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from .embeddings import EMBEDDING_MODEL_NAME, compute_mock_embedding


def backfill_embeddings_once(session_factory: sessionmaker, batch_size: int = 50) -> int:
    """Embeds up to `batch_size` chunks that don't have one yet. This is the
    kind of bulk, latency-insensitive work a background worker is for: the
    API stays fully functional (retrieval doesn't require embeddings to
    exist - it uses the TF-IDF proxy either way) whether or not this
    process is running."""
    with session_factory() as session:
        rows = session.execute(
            select(TranscriptChunkRow).where(TranscriptChunkRow.embedding.is_(None)).limit(batch_size)
        ).scalars().all()
        for row in rows:
            row.embedding = compute_mock_embedding(row.text)
            row.embedding_model = EMBEDDING_MODEL_NAME
        session.commit()
        return len(rows)


def main() -> None:
    database_url = os.environ["DATABASE_URL"]
    poll_seconds = int(os.environ.get("CARECALL_WORKER_POLL_SECONDS", "5"))
    session_factory = create_session_factory(database_url)

    print(f"carecall-worker: polling every {poll_seconds}s for chunks needing embeddings")
    while True:
        processed = backfill_embeddings_once(session_factory)
        if processed:
            print(f"carecall-worker: embedded {processed} chunk(s)")
        time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
