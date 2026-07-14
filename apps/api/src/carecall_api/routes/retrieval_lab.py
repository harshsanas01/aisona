from typing import Dict, List, Optional

from carecall_application.dto.retrieval_comparison import RetrievalModeResult
from carecall_domain import InvalidDateRangeError
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .. import config

router = APIRouter()


def _require_developer_mode() -> None:
    if not config.DEVELOPER_MODE:
        raise HTTPException(
            status_code=403,
            detail="The Retrieval Comparison Lab is only available in developer/admin mode "
            "(set CARECALL_DEVELOPER_MODE=true).",
        )


class CompareRetrievalRequest(BaseModel):
    question: str = Field(..., min_length=1)
    patient_id: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    limit: Optional[int] = None


def _serialize_result(result: RetrievalModeResult) -> Dict[str, object]:
    return {
        "mode": result.mode,
        "lexical_weight": result.lexical_weight,
        "semantic_weight": result.semantic_weight,
        "reranked": result.reranked,
        "candidates": [
            {
                "chunk_id": c.chunk_id,
                "call_id": c.call_id,
                "patient_id": c.patient_id,
                "patient_name": c.patient_name,
                "date": c.date,
                "turn_start": c.turn_start,
                "turn_end": c.turn_end,
                "quote": c.quote,
                "score": c.score,
            }
            for c in result.candidates
        ],
    }


@router.post("/api/v1/retrieval-lab/compare")
def compare_retrieval_modes(payload: CompareRetrievalRequest, request: Request) -> Dict[str, object]:
    _require_developer_mode()
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail="Transcript corpus is unavailable")
    try:
        results: List[RetrievalModeResult] = container.compare_retrieval_modes.execute(
            payload.question,
            patient_id=payload.patient_id,
            start_date=payload.start_date,
            end_date=payload.end_date,
            limit=payload.limit,
        )
    except InvalidDateRangeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"results": [_serialize_result(r) for r in results]}
