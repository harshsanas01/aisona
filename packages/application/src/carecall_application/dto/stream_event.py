from dataclasses import dataclass, field


@dataclass(frozen=True)
class StreamEvent:
    """One event in the /questions/stream contract: retrieval_started,
    retrieval_completed, answer_delta, citations, completed, or error."""

    event: str
    data: dict = field(default_factory=dict)
