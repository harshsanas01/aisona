from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class QuestionAudit:
    """A complete audit record for one /api/ask request - built to answer
    "why did the system produce this answer?" without ever storing the raw
    question or transcript text in a standard log. Retention is
    hash-by-default: question_preview is only ever populated when the
    deployment explicitly opts in (CARECALL_AUDIT_RETAIN_QUESTION_PREVIEW),
    and even then it is a short, truncated preview - never the full
    question. See docs/security/roles-and-privacy.md for the retention
    policy this implements.

    This record is append-only and never mutated after creation - human
    feedback on the resulting answer is looked up live from Feedback
    records (target_type="answer", target_id=request_id) rather than
    stored here, so the audit trail itself stays immutable."""

    request_id: str
    created_at: str
    question_hash: str
    filters: dict
    storage_mode: str
    retrieval_mode: str
    lexical_weight: float
    semantic_weight: float
    top_k: int
    relevance_threshold: float
    candidate_chunk_ids: Tuple[str, ...]
    selected_evidence_ids: Tuple[str, ...]
    answer_mode: str
    provider: str
    prompt_version: str
    latency_ms: float
    answerable: bool
    confidence: str
    final_citation_call_ids: Tuple[str, ...]
    grounding_checks: dict
    fallback_used: bool
    question_preview: Optional[str] = None
    model_name: Optional[str] = None
    token_usage: Optional[dict] = None
    error_category: Optional[str] = None
