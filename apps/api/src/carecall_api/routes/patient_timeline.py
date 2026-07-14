from typing import Dict, Optional

from carecall_domain import InvalidReviewStatusError, TimelineEvent
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..access_control import require_permission

router = APIRouter()


class UpdateTimelineEventRequest(BaseModel):
    review_status: str = Field(..., min_length=1)
    title: Optional[str] = None
    description: Optional[str] = None


def _serialize_event(event: TimelineEvent) -> Dict[str, object]:
    return {
        "event_id": event.event_id,
        "patient_id": event.patient_id,
        "event_type": event.event_type,
        "title": event.title,
        "description": event.description,
        "observed_date": event.observed_date,
        "source_call_id": event.source_call_id,
        "source_turn_start": event.source_turn_start,
        "source_turn_end": event.source_turn_end,
        "quote": event.quote,
        "confidence": event.confidence,
        "extraction_method": event.extraction_method,
        "review_status": event.review_status,
        "created_at": event.created_at,
        "updated_at": event.updated_at,
    }


@router.get("/api/v1/patients/{patient_id}")
def get_patient(patient_id: str, request: Request) -> Dict[str, object]:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail="Transcript corpus is unavailable")
    patient = container.get_patient.execute(patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    events = container.get_patient_timeline.execute(patient_id)
    patterns = container.get_patient_patterns.execute(patient_id)
    return {
        "id": patient.id,
        "name": patient.name,
        "age": patient.age,
        "timeline_event_count": len(events),
        "unreviewed_event_count": sum(1 for e in events if e.review_status == "unreviewed"),
        "pattern_count": len(patterns),
        "attention_pattern_count": sum(1 for p in patterns if p.severity in ("attention", "high_attention")),
    }


@router.get("/api/v1/patients/{patient_id}/timeline")
def get_patient_timeline(
    patient_id: str,
    request: Request,
    event_type: Optional[str] = None,
    review_status: Optional[str] = None,
) -> Dict[str, object]:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail="Transcript corpus is unavailable")
    if container.get_patient.execute(patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    events = container.get_patient_timeline.execute(
        patient_id, event_type=event_type, review_status=review_status,
    )
    return {"timeline_events": [_serialize_event(e) for e in events]}


@router.post("/api/v1/patients/{patient_id}/timeline/rebuild", dependencies=[Depends(require_permission("manage_tasks"))])
def rebuild_patient_timeline(patient_id: str, request: Request) -> Dict[str, object]:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail="Transcript corpus is unavailable")
    if container.get_patient.execute(patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    events = container.rebuild_patient_timeline.execute(patient_id)
    return {"timeline_events": [_serialize_event(e) for e in events]}


@router.patch("/api/v1/timeline-events/{event_id}", dependencies=[Depends(require_permission("review"))])
def update_timeline_event(
    event_id: str, payload: UpdateTimelineEventRequest, request: Request,
) -> Dict[str, object]:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail="Transcript corpus is unavailable")
    try:
        updated = container.update_timeline_event.execute(
            event_id, payload.review_status, title=payload.title, description=payload.description,
        )
    except InvalidReviewStatusError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="Timeline event not found")
    return _serialize_event(updated)
