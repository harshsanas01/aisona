from abc import ABC, abstractmethod
from typing import List

from carecall_domain import Citation


class CitationValidator(ABC):
    """Final structural check before citations are returned to the caller:
    every citation must reference a real, well-formed turn range and a
    non-empty quote. Citations are always built server-side from trusted
    chunk metadata (never from generator output), so under normal operation
    nothing here should ever fail - this is a last line of defense against a
    future bug in citation construction, not a data-quality filter."""

    @abstractmethod
    def validate(self, citations: List[Citation]) -> List[Citation]: ...
