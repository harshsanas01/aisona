from dataclasses import dataclass, field
from typing import List, Optional

from carecall_domain import Citation


@dataclass(frozen=True)
class AskQuestionResult:
    question: str
    answer: str
    answerable: bool
    confidence: str
    citations: List[Citation] = field(default_factory=list)
    retrieval_debug: dict = field(default_factory=dict)
    filters: dict = field(default_factory=dict)
    # Additive fields consumed only by the audit trail (see
    # RecordQuestionAuditUseCase) - never part of the public /api/ask
    # response body, so adding to this dataclass can't change the wire API.
    candidate_chunk_ids: List[str] = field(default_factory=list)
    selected_evidence_ids: List[str] = field(default_factory=list)
    model_name: Optional[str] = None
    prompt_version: str = "v1"
    usage: Optional[dict] = None
    fallback_used: bool = False
    grounding_checks: dict = field(default_factory=dict)
