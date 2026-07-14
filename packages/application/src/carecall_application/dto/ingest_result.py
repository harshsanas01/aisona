from dataclasses import dataclass


@dataclass(frozen=True)
class IngestCallResult:
    call_id: str
    status: str  # "created" | "duplicate" | "error"
    chunk_count: int = 0
    error: str = ""
