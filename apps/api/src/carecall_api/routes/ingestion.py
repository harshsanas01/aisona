from typing import List

from carecall_domain import Call, DuplicateCallError, Patient, Turn
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

router = APIRouter()

MAX_BATCH_SIZE = 20


class TurnIn(BaseModel):
    speaker: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)


class PatientIn(BaseModel):
    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    age: int = Field(..., ge=0, le=130)


class CallIn(BaseModel):
    call_id: str = Field(..., min_length=1)
    date: str = Field(..., min_length=1)
    patient: PatientIn
    duration_seconds: int = Field(..., ge=0)
    turns: List[TurnIn] = Field(..., min_length=1)


class BatchIngestRequest(BaseModel):
    calls: List[CallIn] = Field(..., min_length=1, max_length=MAX_BATCH_SIZE)


class IngestResultOut(BaseModel):
    call_id: str
    status: str
    chunk_count: int = 0
    error: str = ""


def _to_domain_call(payload: CallIn) -> Call:
    return Call(
        call_id=payload.call_id,
        date=payload.date,
        patient=Patient(id=payload.patient.id, name=payload.patient.name, age=payload.patient.age),
        duration_seconds=payload.duration_seconds,
        turns=[Turn(speaker=t.speaker, text=t.text) for t in payload.turns],
    )


@router.post("/api/calls", status_code=status.HTTP_201_CREATED, response_model=IngestResultOut)
def ingest_call(payload: CallIn, request: Request) -> IngestResultOut:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail="Transcript corpus is unavailable")

    call = _to_domain_call(payload)
    try:
        result = container.ingest_call.execute(call)
    except DuplicateCallError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return IngestResultOut(call_id=result.call_id, status=result.status, chunk_count=result.chunk_count)


@router.post("/api/calls/batch", response_model=List[IngestResultOut])
def ingest_calls_batch(payload: BatchIngestRequest, request: Request) -> List[IngestResultOut]:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail="Transcript corpus is unavailable")

    results: List[IngestResultOut] = []
    for item in payload.calls:
        call = _to_domain_call(item)
        try:
            result = container.ingest_call.execute(call)
            results.append(IngestResultOut(call_id=result.call_id, status=result.status, chunk_count=result.chunk_count))
        except DuplicateCallError as exc:
            results.append(IngestResultOut(call_id=item.call_id, status="duplicate", chunk_count=0, error=str(exc)))
        except Exception as exc:  # one bad record must not abort the rest of the batch
            results.append(IngestResultOut(call_id=item.call_id, status="error", chunk_count=0, error=str(exc)))
    return results
