from typing import Dict, List, Optional

from carecall_domain import Feedback, InvalidFeedbackError
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..access_control import require_permission

router = APIRouter()


class SubmitFeedbackRequest(BaseModel):
    target_type: str = Field(..., min_length=1)
    target_id: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    actor: str = Field(..., min_length=1)
    comment: Optional[str] = None
    corrected_value: Optional[str] = None
    prompt_version: Optional[str] = None
    retrieval_version: Optional[str] = None
    model_version: Optional[str] = None


def _serialize_feedback(record: Feedback) -> Dict[str, object]:
    return {
        "feedback_id": record.feedback_id,
        "target_type": record.target_type,
        "target_id": record.target_id,
        "category": record.category,
        "actor": record.actor,
        "created_at": record.created_at,
        "comment": record.comment,
        "corrected_value": record.corrected_value,
        "prompt_version": record.prompt_version,
        "retrieval_version": record.retrieval_version,
        "model_version": record.model_version,
    }


@router.post("/api/v1/feedback", dependencies=[Depends(require_permission("review"))])
def submit_feedback(payload: SubmitFeedbackRequest, request: Request) -> Dict[str, object]:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail="Transcript corpus is unavailable")
    try:
        created = container.submit_feedback.execute(
            target_type=payload.target_type,
            target_id=payload.target_id,
            category=payload.category,
            actor=payload.actor,
            comment=payload.comment,
            corrected_value=payload.corrected_value,
            prompt_version=payload.prompt_version,
            retrieval_version=payload.retrieval_version,
            model_version=payload.model_version,
        )
    except InvalidFeedbackError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _serialize_feedback(created)


@router.get("/api/v1/feedback")
def list_feedback(
    request: Request,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, object]:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail="Transcript corpus is unavailable")
    records: List[Feedback] = container.list_feedback.execute(
        target_type=target_type, target_id=target_id, category=category, limit=limit,
    )
    return {"feedback": [_serialize_feedback(r) for r in records]}


@router.get("/api/v1/feedback/summary")
def get_feedback_summary(request: Request) -> Dict[str, object]:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail="Transcript corpus is unavailable")
    summary = container.get_feedback_summary.execute()
    return {
        "total": summary.total,
        "by_target_type": summary.by_target_type,
        "by_category": summary.by_category,
    }
