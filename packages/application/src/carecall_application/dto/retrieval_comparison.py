from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class RetrievalModeCandidate:
    chunk_id: str
    call_id: str
    patient_id: str
    patient_name: str
    date: str
    turn_start: int
    turn_end: int
    quote: str
    score: float


@dataclass(frozen=True)
class RetrievalModeResult:
    mode: str
    lexical_weight: float
    semantic_weight: float
    reranked: bool
    candidates: List[RetrievalModeCandidate] = field(default_factory=list)
