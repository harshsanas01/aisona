from typing import List

from pydantic import BaseModel, Field


class OpenAIStructuredAnswer(BaseModel):
    """Validates the raw JSON payload requested from the OpenAI chat
    completion before it is trusted for anything - a malformed or
    unexpected payload should fail validation and fall back to the mock
    generator rather than propagate an unvalidated dict through the system.
    """

    answerable: bool = False
    answer: str = ""
    used_evidence_ids: List[str] = Field(default_factory=list)
    confidence: str = "low"
