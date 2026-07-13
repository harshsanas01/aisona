class DomainError(Exception):
    """Base class for all CareCall domain errors."""


class TranscriptDataError(DomainError):
    """Raised when the transcript corpus is missing or malformed."""


class InvalidDateRangeError(DomainError):
    """Raised when a requested start_date is after end_date."""


class DuplicateCallError(DomainError):
    """Raised when a call with an already-known external call id is ingested again."""
