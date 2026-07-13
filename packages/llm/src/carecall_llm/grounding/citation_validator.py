from typing import List

from carecall_application.ports.citation_validator import CitationValidator
from carecall_domain import Citation


class StructuralCitationValidator(CitationValidator):
    """Defends against a malformed citation ever reaching the caller: a
    non-empty call id and quote, and a turn range that's internally
    consistent (start >= 1, end >= start). Citations are always built
    server-side from trusted chunk metadata, so under normal operation
    nothing here should ever be dropped - this is a last-line structural
    check, not a data-quality filter."""

    def validate(self, citations: List[Citation]) -> List[Citation]:
        valid = []
        for citation in citations:
            if not citation.call_id or not citation.quote or not citation.quote.strip():
                continue
            if citation.turn_start < 1 or citation.turn_end < citation.turn_start:
                continue
            valid.append(citation)
        return valid
