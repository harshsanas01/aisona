import json
from pathlib import Path
from typing import List

from carecall_domain import Call, DuplicateCallError, Patient, TranscriptDataError, Turn
from pydantic import BaseModel, ConfigDict


class _TurnModel(BaseModel):
    model_config = ConfigDict(extra="ignore")
    speaker: str
    text: str


class _PatientModel(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    age: int


class _CallModel(BaseModel):
    model_config = ConfigDict(extra="ignore")
    call_id: str
    date: str
    patient: _PatientModel
    duration_seconds: int
    turns: List[_TurnModel]


def load_calls_from_json(path: Path) -> List[Call]:
    """Parse a JSON fixture file of the shape {"calls": [...]}, validating
    structure and rejecting duplicate call ids. Used for demo-mode bootstrap
    and as the fixture-ingestion path in tests; the same shape is accepted
    by POST /api/calls for durable ingestion in production-like mode."""
    if not path.exists():
        raise TranscriptDataError(f"Missing transcript data file: {path}")

    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise TranscriptDataError(f"Malformed transcript JSON: {exc}") from exc

    if "calls" not in raw or not isinstance(raw["calls"], list):
        raise TranscriptDataError('Transcript JSON must contain a top-level "calls" array')

    calls: List[Call] = []
    seen_ids = set()
    for index, item in enumerate(raw["calls"], start=1):
        try:
            parsed = _CallModel.model_validate(item)
        except Exception as exc:
            raise TranscriptDataError(f"Invalid call entry at index {index}: {exc}") from exc
        if parsed.call_id in seen_ids:
            raise DuplicateCallError(f"Duplicate call ID found: {parsed.call_id}")
        seen_ids.add(parsed.call_id)
        calls.append(Call(
            call_id=parsed.call_id,
            date=parsed.date,
            patient=Patient(id=parsed.patient.id, name=parsed.patient.name, age=parsed.patient.age),
            duration_seconds=parsed.duration_seconds,
            turns=[Turn(speaker=t.speaker, text=t.text) for t in parsed.turns],
        ))
    return calls
