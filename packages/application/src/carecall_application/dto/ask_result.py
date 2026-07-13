from dataclasses import dataclass, field
from typing import List

from carecall_domain import Citation


@dataclass(frozen=True)
class AskQuestionResult:
    question: str
    answer: str
    answerable: bool
    confidence: str
    citations: List[Citation] = field(default_factory=list)
    retrieval_debug: dict = field(default_factory=dict)
    filters: dict = field(default_factory=dict)
