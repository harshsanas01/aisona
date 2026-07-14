from abc import ABC, abstractmethod
from typing import List

from carecall_domain import Chunk

from ..dto.answer import GroundedAnswer


class AnswerGenerator(ABC):
    """Port for turning (question, evidence) into a grounded answer.

    Implementations (mock, OpenAI, ...) may return which evidence chunk ids
    they used, but they must NEVER return final call ids, patient ids, turn
    numbers, quotes, or dates directly - citation reconstruction always
    happens from server-owned chunk metadata, never from generator output.
    """

    @abstractmethod
    def generate(self, question: str, evidence: List[Chunk], filters: dict) -> GroundedAnswer: ...
