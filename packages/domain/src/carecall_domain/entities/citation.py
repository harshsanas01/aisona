from dataclasses import dataclass


@dataclass(frozen=True)
class Citation:
    call_id: str
    patient_id: str
    patient_name: str
    date: str
    turn_start: int
    turn_end: int
    quote: str
