from typing import Dict, Optional

from carecall_domain import InvalidReviewStatusError, PersonMention
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..access_control import require_permission

router = APIRouter()


class UpdatePersonMentionRequest(BaseModel):
    review_status: str = Field(..., min_length=1)
    corrected_relationship_type: Optional[str] = None
    corrected_name: Optional[str] = None


def _serialize_mention(mention: PersonMention) -> Dict[str, object]:
    return {
        "mention_id": mention.mention_id,
        "patient_id": mention.patient_id,
        "source_call_id": mention.source_call_id,
        "source_turn": mention.source_turn,
        "quote": mention.quote,
        "role_label": mention.role_label,
        "relationship_type": mention.relationship_type,
        "mentioned_name": mention.mentioned_name,
        "confidence": mention.confidence,
        "extraction_method": mention.extraction_method,
        "review_status": mention.review_status,
        "created_at": mention.created_at,
        "updated_at": mention.updated_at,
    }


@router.get("/api/v1/patients/{patient_id}/people")
def get_patient_person_mentions(
    patient_id: str,
    request: Request,
    relationship_type: Optional[str] = None,
    review_status: Optional[str] = None,
) -> Dict[str, object]:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail="Transcript corpus is unavailable")
    if container.get_patient.execute(patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    mentions = container.get_patient_person_mentions.execute(
        patient_id, relationship_type=relationship_type, review_status=review_status,
    )
    return {"person_mentions": [_serialize_mention(m) for m in mentions]}


@router.post("/api/v1/patients/{patient_id}/people/rebuild", dependencies=[Depends(require_permission("manage_tasks"))])
def rebuild_patient_person_mentions(patient_id: str, request: Request) -> Dict[str, object]:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail="Transcript corpus is unavailable")
    if container.get_patient.execute(patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    mentions = container.rebuild_patient_person_mentions.execute(patient_id)
    return {"person_mentions": [_serialize_mention(m) for m in mentions]}


@router.patch("/api/v1/person-mentions/{mention_id}", dependencies=[Depends(require_permission("review"))])
def update_person_mention(
    mention_id: str, payload: UpdatePersonMentionRequest, request: Request,
) -> Dict[str, object]:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail="Transcript corpus is unavailable")
    try:
        updated = container.update_person_mention.execute(
            mention_id,
            payload.review_status,
            corrected_relationship_type=payload.corrected_relationship_type,
            corrected_name=payload.corrected_name,
        )
    except InvalidReviewStatusError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="Person mention not found")
    return _serialize_mention(updated)
