from dataclasses import dataclass


@dataclass(frozen=True)
class PatternEvidenceRef:
    """One exact evidence reference backing a detected pattern - always
    reconstructed from a real TimelineEvent, never invented."""

    timeline_event_id: str
    call_id: str
    turn_start: int
    turn_end: int
    quote: str
