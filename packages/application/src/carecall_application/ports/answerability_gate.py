from abc import ABC, abstractmethod
from typing import List

from carecall_domain import Chunk


class AnswerabilityGate(ABC):
    """Decides whether retrieved evidence is sufficient to even attempt an
    answer, before any generation happens. This is the primary defense
    against confidently answering out-of-domain or unsupported questions
    (e.g. "What is today's weather in LA?") - it runs regardless of which
    AnswerGenerator is configured, so a bad LLM response can never turn an
    ungrounded question into a confident one.
    """

    @abstractmethod
    def is_unanswerable(self, question: str, chunks: List[Chunk]) -> bool: ...
