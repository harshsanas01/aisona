from typing import List, Optional

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=400)
    patient_id: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class CitationOut(BaseModel):
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
    citations: List[CitationOut]
    retrieval_debug: dict
    filters: dict
    # Correlates this answer with its audit-trail record (see
    # GET /api/v1/audit/questions/{request_id} and the "Why this answer?"
    # developer drawer) - never used to look up the raw question text.
    request_id: Optional[str] = None
