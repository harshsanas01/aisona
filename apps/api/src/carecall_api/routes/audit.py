from typing import Dict, List, Optional

from carecall_domain import Feedback, QuestionAudit
from fastapi import APIRouter, HTTPException, Request

from .. import config

router = APIRouter()


def _require_developer_mode() -> None:
    if not config.DEVELOPER_MODE:
        raise HTTPException(
            status_code=403,
            detail="The audit trail is only available in developer/admin mode "
            "(set CARECALL_DEVELOPER_MODE=true).",
        )


def _feedback_summary(records: List[Feedback]) -> Dict[str, object]:
    # Computed live from the feedback table rather than read off the stored
    # QuestionAudit row - the audit record itself is append-only/immutable,
    # so it is never rewritten as feedback arrives after the fact.
    by_category: Dict[str, int] = {}
    for record in records:
        by_category[record.category] = by_category.get(record.category, 0) + 1
    return {"total": len(records), "by_category": by_category}


def _serialize_audit(record: QuestionAudit, feedback_summary: Dict[str, object]) -> Dict[str, object]:
    return {
        "request_id": record.request_id,
        "created_at": record.created_at,
        "question_hash": record.question_hash,
        "question_preview": record.question_preview,
        "filters": record.filters,
        "storage_mode": record.storage_mode,
        "retrieval_mode": record.retrieval_mode,
        "lexical_weight": record.lexical_weight,
        "semantic_weight": record.semantic_weight,
        "top_k": record.top_k,
        "relevance_threshold": record.relevance_threshold,
        "candidate_chunk_ids": list(record.candidate_chunk_ids),
        "selected_evidence_ids": list(record.selected_evidence_ids),
        "answer_mode": record.answer_mode,
        "provider": record.provider,
        "model_name": record.model_name,
        "prompt_version": record.prompt_version,
        "token_usage": record.token_usage,
        "latency_ms": record.latency_ms,
        "answerable": record.answerable,
        "confidence": record.confidence,
        "final_citation_call_ids": list(record.final_citation_call_ids),
        "grounding_checks": record.grounding_checks,
        "fallback_used": record.fallback_used,
        "error_category": record.error_category,
        "feedback_summary": feedback_summary,
    }


@router.get("/api/v1/audit/questions")
def list_audit_questions(
    request: Request, answerable: Optional[bool] = None, limit: int = 50,
) -> Dict[str, object]:
    _require_developer_mode()
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail="Transcript corpus is unavailable")
    records = container.list_question_audit.execute(answerable=answerable, limit=limit)
    return {
        "audit_records": [
            _serialize_audit(
                r, _feedback_summary(container.list_feedback.execute(target_type="answer", target_id=r.request_id)),
            )
            for r in records
        ]
    }


@router.get("/api/v1/audit/questions/{request_id}")
def get_audit_question(request_id: str, request: Request) -> Dict[str, object]:
    _require_developer_mode()
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail="Transcript corpus is unavailable")
    record = container.get_question_audit.execute(request_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Audit record not found")
    feedback_records = container.list_feedback.execute(target_type="answer", target_id=request_id)
    return _serialize_audit(record, _feedback_summary(feedback_records))
