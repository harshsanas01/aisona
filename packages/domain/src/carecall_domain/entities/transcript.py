from dataclasses import dataclass
from typing import List

from .patient import Patient


@dataclass(frozen=True)
class Turn:
    speaker: str
    text: str


@dataclass(frozen=True)
class Call:
    call_id: str
    date: str
    patient: Patient
    duration_seconds: int
    turns: List[Turn]
