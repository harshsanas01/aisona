from typing import Callable, List, Optional

from carecall_domain import Call, Chunk

from ..dto.ingest_result import IngestCallResult
from ..ports.repositories import CallRepository, ChunkRepository


class IngestCallUseCase:
    """Ingests one complete call transcript.

    - Durability: CallRepository.add_call() persists the patient (upsert),
      the call, and every turn as a single transaction (PostgreSQL mode) or
      atomically in memory (demo mode).
    - Idempotency: add_call() raises DuplicateCallError on a re-ingested
      external call id - the caller (delivery layer) maps that to HTTP 409.
    - Searchability: after the call and its chunks are persisted,
      on_ingested (if provided) is called so the retrieval index can be
      refreshed - without this, a newly ingested call would not become
      searchable until the process restarts.
    """

    def __init__(
        self,
        call_repository: CallRepository,
        chunk_repository: ChunkRepository,
        chunk_builder: Callable[[Call], List[Chunk]],
        on_ingested: Optional[Callable[[], None]] = None,
    ):
        self.call_repository = call_repository
        self.chunk_repository = chunk_repository
        self.chunk_builder = chunk_builder
        self.on_ingested = on_ingested

    def execute(self, call: Call) -> IngestCallResult:
        self.call_repository.add_call(call)
        chunks = self.chunk_builder(call)
        self.chunk_repository.add_chunks(chunks)
        if self.on_ingested:
            self.on_ingested()
        return IngestCallResult(call_id=call.call_id, status="created", chunk_count=len(chunks))
