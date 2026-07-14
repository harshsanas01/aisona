from abc import ABC, abstractmethod
from typing import List

from carecall_domain import Chunk


class AnswerabilityGate(ABC):
    """Decides whether a question can be answered at all - both before
    retrieval (query validation / scope classification) and after
    (evidence sufficiency), before any generation happens. This is the
    primary defense against confidently answering out-of-domain or
    unsupported questions (e.g. "What is today's weather in LA?") - it runs
    regardless of which AnswerGenerator is configured, so a bad LLM
    response can never turn an ungrounded question into a confident one.
    """

    def is_query_out_of_scope(self, question: str) -> bool:
        """Query validation / scope classification, run BEFORE retrieval.
        Default: no rejection - override to reject e.g. general-knowledge
        or medical-advice requests without spending a retrieval call on
        them."""
        return False

    @abstractmethod
    def is_unanswerable(self, question: str, chunks: List[Chunk]) -> bool: ...
