from typing import Dict, Optional

from carecall_domain import Brief, InvalidBriefRequestError
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..access_control import require_permission

router = APIRouter()


class GenerateBriefRequest(BaseModel):
    type: str = Field(..., min_length=1)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    patient_id: Optional[str] = None
    include_resolved: bool = False
    answer_mode: str = "mock"


def _serialize_brief(brief: Brief) -> Dict[str, object]:
    return {
        "brief_id": brief.brief_id,
        "brief_type": brief.brief_type,
        "start_date": brief.start_date,
        "end_date": brief.end_date,
        "patient_id": brief.patient_id,
        "include_resolved": brief.include_resolved,
        "model_version": brief.model_version,
        "prompt_version": brief.prompt_version,
        "generated_at": brief.generated_at,
        "created_at": brief.created_at,
        "updated_at": brief.updated_at,
        "bullets": [
            {
                "bullet_id": b.bullet_id,
                "section": b.section,
                "patient_id": b.patient_id,
                "patient_name": b.patient_name,
                "summary": b.summary,
                "related_timeline_event_ids": list(b.related_timeline_event_ids),
                "related_pattern_id": b.related_pattern_id,
                "related_task_id": b.related_task_id,
                "evidence": [
                    {
                        "timeline_event_id": e.timeline_event_id,
                        "call_id": e.call_id,
                        "turn_start": e.turn_start,
                        "turn_end": e.turn_end,
                        "quote": e.quote,
                    }
                    for e in b.evidence
                ],
            }
            for b in brief.bullets
        ],
    }


@router.post("/api/v1/briefs", status_code=201, dependencies=[Depends(require_permission("manage_tasks"))])
def generate_brief(payload: GenerateBriefRequest, request: Request) -> Dict[str, object]:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail="Transcript corpus is unavailable")
    if payload.patient_id is not None and container.get_patient.execute(payload.patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    prose_generator = container.brief_prose_generators.get(payload.answer_mode)
    try:
        brief = container.generate_brief.execute(
            brief_type=payload.type,
            start_date=payload.start_date,
            end_date=payload.end_date,
            patient_id=payload.patient_id,
            include_resolved=payload.include_resolved,
            prose_generator=prose_generator,
        )
    except InvalidBriefRequestError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _serialize_brief(brief)


@router.get("/api/v1/briefs")
def list_briefs(
    request: Request, type: Optional[str] = None, patient_id: Optional[str] = None,
) -> Dict[str, object]:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail="Transcript corpus is unavailable")
    briefs = container.list_briefs.execute(brief_type=type, patient_id=patient_id)
    return {"briefs": [_serialize_brief(b) for b in briefs]}


@router.get("/api/v1/briefs/{brief_id}")
def get_brief(brief_id: str, request: Request) -> Dict[str, object]:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail="Transcript corpus is unavailable")
    brief = container.get_brief.execute(brief_id)
    if brief is None:
        raise HTTPException(status_code=404, detail="Brief not found")
    return _serialize_brief(brief)


@router.post("/api/v1/briefs/{brief_id}/regenerate", dependencies=[Depends(require_permission("manage_tasks"))])
def regenerate_brief(brief_id: str, request: Request, answer_mode: str = "mock") -> Dict[str, object]:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail="Transcript corpus is unavailable")
    prose_generator = container.brief_prose_generators.get(answer_mode)
    brief = container.regenerate_brief.execute(brief_id, prose_generator=prose_generator)
    if brief is None:
        raise HTTPException(status_code=404, detail="Brief not found")
    return _serialize_brief(brief)
