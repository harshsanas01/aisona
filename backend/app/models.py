from typing import List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


class Turn(BaseModel):
    model_config = ConfigDict(extra='ignore')
    speaker: str
    text: str


class Patient(BaseModel):
    model_config = ConfigDict(extra='ignore')
    id: str
    name: str
    age: int


class TranscriptCall(BaseModel):
    model_config = ConfigDict(extra='ignore')
    call_id: str
    date: str
    patient: Patient
    duration_seconds: int
    turns: List[Turn]


class TranscriptCorpus(BaseModel):
    calls: List[TranscriptCall]


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=400)
    patient_id: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class Citation(BaseModel):
    call_id: str
    patient_id: str
    patient_name: str
    date: str
    turn_start: int
    turn_end: int
    quote: str


class AskResponse(BaseModel):
    question: str
    answer: str
    answerable: bool
    confidence: str
    citations: List[Citation]
    retrieval_debug: dict
