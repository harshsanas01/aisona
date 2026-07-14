from typing import Dict, Optional

from carecall_domain import InvalidReviewStatusError, PatientPattern
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..access_control import require_permission

router = APIRouter()


class UpdatePatternRequest(BaseModel):
    reviewed_status: str = Field(..., min_length=1)


def _serialize_pattern(pattern: PatientPattern) -> Dict[str, object]:
    return {
        "pattern_id": pattern.pattern_id,
        "patient_id": pattern.patient_id,
        "pattern_type": pattern.pattern_type,
        "title": pattern.title,
        "summary": pattern.summary,
        "status": pattern.status,
        "severity": pattern.severity,
        "first_observed_date": pattern.first_observed_date,
        "latest_observed_date": pattern.latest_observed_date,
        "related_timeline_event_ids": list(pattern.related_timeline_event_ids),
        "related_call_ids": list(pattern.related_call_ids),
        "evidence": [
            {
                "timeline_event_id": e.timeline_event_id,
                "call_id": e.call_id,
                "turn_start": e.turn_start,
                "turn_end": e.turn_end,
                "quote": e.quote,
            }
            for e in pattern.evidence
        ],
        "detector_version": pattern.detector_version,
        "reviewed_status": pattern.reviewed_status,
        "created_at": pattern.created_at,
        "updated_at": pattern.updated_at,
    }


@router.get("/api/v1/patients/{patient_id}/patterns")
def get_patient_patterns(
    patient_id: str,
    request: Request,
    status: Optional[str] = None,
    severity: Optional[str] = None,
) -> Dict[str, object]:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail="Transcript corpus is unavailable")
    if container.get_patient.execute(patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    patterns = container.get_patient_patterns.execute(patient_id, status=status, severity=severity)
    return {"patterns": [_serialize_pattern(p) for p in patterns]}


@router.post("/api/v1/patients/{patient_id}/patterns/rebuild", dependencies=[Depends(require_permission("manage_tasks"))])
def rebuild_patient_patterns(patient_id: str, request: Request) -> Dict[str, object]:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail="Transcript corpus is unavailable")
    if container.get_patient.execute(patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    patterns = container.rebuild_patient_patterns.execute(patient_id)
    return {"patterns": [_serialize_pattern(p) for p in patterns]}


@router.patch("/api/v1/patterns/{pattern_id}", dependencies=[Depends(require_permission("review"))])
def update_pattern(pattern_id: str, payload: UpdatePatternRequest, request: Request) -> Dict[str, object]:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail="Transcript corpus is unavailable")
    try:
        updated = container.update_pattern.execute(pattern_id, payload.reviewed_status)
    except InvalidReviewStatusError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return _serialize_pattern(updated)
