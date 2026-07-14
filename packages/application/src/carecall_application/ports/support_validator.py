from abc import ABC, abstractmethod
from typing import List

from carecall_domain import Chunk


class SupportValidator(ABC):
    """Post-generation check (grounding pipeline step 10): does the evidence
    actually selected as citations plausibly support this question, or did
    retrieval/generation drift onto an unrelated call? This is what stops a
    generator from confidently answering "Did Gus fall?" using evidence
    about an entirely different patient - the primary defense is retrieval
    ranking + the answerability gate, but this runs after generation as a
    last check before the answer is allowed to reach the caller.
    """

    @abstractmethod
    def is_supported(self, question: str, evidence_chunks: List[Chunk]) -> bool: ...
