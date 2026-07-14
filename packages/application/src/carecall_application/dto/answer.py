from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class GroundedAnswer:
    """Structured output of an AnswerGenerator. used_evidence_ids references
    Chunk.chunk_id values from the evidence that was supplied to the
    generator - the application layer is responsible for turning those ids
    back into real Citation objects from trusted chunk metadata."""

    answerable: bool
    answer: str
    used_evidence_ids: List[str] = field(default_factory=list)
    confidence: str = "low"
    model_name: Optional[str] = None
    prompt_version: str = "v1"
    usage: Optional[dict] = None
    used_fallback: bool = False
