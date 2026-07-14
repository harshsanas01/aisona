class DomainError(Exception):
    """Base class for all CareCall domain errors."""


class TranscriptDataError(DomainError):
    """Raised when the transcript corpus is missing or malformed."""


class InvalidDateRangeError(DomainError):
    """Raised when a requested start_date is after end_date."""


class DuplicateCallError(DomainError):
    """Raised when a call with an already-known external call id is ingested again."""


class InvalidReviewStatusError(DomainError):
    """Raised when a timeline event's review_status is set to a value
    outside TIMELINE_REVIEW_STATUSES."""


class InvalidTaskStatusTransitionError(DomainError):
    """Raised when a task status change isn't listed in
    TASK_STATUS_TRANSITIONS for the task's current status."""


class InvalidTaskFieldError(DomainError):
    """Raised when a task's priority or category is outside its allowed
    vocabulary (TASK_PRIORITIES / TASK_CATEGORIES)."""


class InvalidBriefRequestError(DomainError):
    """Raised when a brief request's type is outside BRIEF_TYPES or its
    date range is invalid (start_date after end_date)."""


class InvalidFeedbackError(DomainError):
    """Raised when feedback's target_type is outside FEEDBACK_TARGET_TYPES,
    or its category isn't valid for that target_type."""
