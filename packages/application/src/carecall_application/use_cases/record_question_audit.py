import uuid
from datetime import datetime, timezone
from typing import Optional

from carecall_domain import QuestionAudit, hash_question, redact_question_preview

from ..dto.ask_result import AskQuestionResult
from ..ports.repositories import QuestionAuditRepository


class RecordQuestionAuditUseCase:
    """Builds and persists one QuestionAudit record per /api/ask request.
    Called from the API route layer (not from AskQuestionUseCase itself) so
    the core grounding pipeline stays free of audit/logging concerns.

    Privacy: the raw question text is never passed to the repository - only
    its hash, and (only when retain_question_preview is explicitly enabled)
    a short, truncated preview. See docs/security/roles-and-privacy.md."""

    def __init__(self, audit_repository: QuestionAuditRepository, *, retain_question_preview: bool = False):
        self.audit_repository = audit_repository
        self.retain_question_preview = retain_question_preview

    def execute(
        self,
        result: AskQuestionResult,
        *,
        storage_mode: str,
        retrieval_mode: str,
        lexical_weight: float,
        semantic_weight: float,
        top_k: int,
        relevance_threshold: float,
        answer_mode: str,
        provider: str,
        latency_ms: float,
        error_category: Optional[str] = None,
    ) -> QuestionAudit:
        record = QuestionAudit(
            request_id=f"req-{uuid.uuid4().hex[:16]}",
            created_at=datetime.now(timezone.utc).isoformat(),
            question_hash=hash_question(result.question),
            question_preview=redact_question_preview(result.question) if self.retain_question_preview else None,
            filters=result.filters,
            storage_mode=storage_mode,
            retrieval_mode=retrieval_mode,
            lexical_weight=lexical_weight,
            semantic_weight=semantic_weight,
            top_k=top_k,
            relevance_threshold=relevance_threshold,
            candidate_chunk_ids=tuple(result.candidate_chunk_ids),
            selected_evidence_ids=tuple(result.selected_evidence_ids),
            answer_mode=answer_mode,
            provider=provider,
            model_name=result.model_name,
            prompt_version=result.prompt_version,
            token_usage=result.usage,
            latency_ms=latency_ms,
            answerable=result.answerable,
            confidence=result.confidence,
            final_citation_call_ids=tuple(c.call_id for c in result.citations),
            grounding_checks=result.grounding_checks,
            fallback_used=result.fallback_used,
            error_category=error_category,
        )
        return self.audit_repository.create(record)
