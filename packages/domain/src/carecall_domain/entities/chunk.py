from dataclasses import dataclass
from typing import List, Optional

from .citation import Citation
from .transcript import Turn


@dataclass(frozen=True)
class Chunk:
    """An overlapping dialogue window (2-4 consecutive turns) that preserves
    the original turn numbers and exact transcript text. This is the unit of
    retrieval and the unit of evidence a citation is built from."""

    chunk_id: str
    call_id: str
    patient_id: str
    patient_name: str
    date: str
    turn_start: int
    turn_end: int
    turns: List[Turn]
    metadata_text: str
    text: str

    def to_citation(self, quote: Optional[str] = None) -> Citation:
        excerpt = quote or self.text[:180]
        return Citation(
            call_id=self.call_id,
            patient_id=self.patient_id,
            patient_name=self.patient_name,
            date=self.date,
            turn_start=self.turn_start,
            turn_end=self.turn_end,
            quote=excerpt,
        )
