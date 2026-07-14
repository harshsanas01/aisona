from dataclasses import dataclass
from typing import Optional

from ..exceptions import InvalidDateRangeError


@dataclass(frozen=True)
class DateRange:
    """An optional [start, end] filter over ISO 'YYYY-MM-DD' date strings.

    Dates are kept as strings (not parsed into datetime objects) because the
    corpus already stores them in sortable ISO form, so plain string
    comparison is correct and avoids a timezone/parsing dependency.
    """

    start: Optional[str] = None
    end: Optional[str] = None

    def __post_init__(self) -> None:
        if self.start and self.end and self.start > self.end:
            raise InvalidDateRangeError(
                f"start_date ({self.start}) must not be after end_date ({self.end})"
            )

    def contains(self, date_str: str) -> bool:
        if self.start and date_str < self.start:
            return False
        if self.end and date_str > self.end:
            return False
        return True

    @property
    def is_empty(self) -> bool:
        return self.start is None and self.end is None
