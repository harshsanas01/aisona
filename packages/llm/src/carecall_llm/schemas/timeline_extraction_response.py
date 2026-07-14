from typing import List

from pydantic import BaseModel, Field


class OpenAICandidateTimelineEvent(BaseModel):
    turn_number: int = 0
    event_type: str = ""
    confidence: str = "low"


class OpenAITimelineExtractionResponse(BaseModel):
    """Validates the raw JSON payload requested from the OpenAI chat
    completion before any of it is trusted. Deliberately has no field for a
    quote, date, or call id - the caller always reconstructs citations from
    the real transcript it already has, never from model output."""

    events: List[OpenAICandidateTimelineEvent] = Field(default_factory=list)
