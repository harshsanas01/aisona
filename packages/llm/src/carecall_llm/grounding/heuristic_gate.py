from typing import List

from carecall_application.ports.answerability_gate import AnswerabilityGate
from carecall_domain import Chunk


class HeuristicAnswerabilityGate(AnswerabilityGate):
    """Rule-based defense against confidently answering questions the
    retrieved evidence does not actually support.

    NOTE: this is the pre-refactor heuristic (string checks), preserved
    as-is during the layered-architecture extraction so behavior does not
    change here. It is replaced by a real multi-stage grounding pipeline
    (query validation, scope classification, evidence/citation validation)
    in a follow-up commit - see docs/architecture/grounding.md and
    docs/adr/0003-server-owned-citations.md.
    """

    def is_unanswerable(self, question: str, chunks: List[Chunk]) -> bool:
        lowered = question.lower()
        if any(term in lowered for term in ["chest pain", "fell recently", "fallen recently", "fall recently"]):
            return True
        if "fall" in lowered and ("did not" in lowered or "no" in lowered or "any participant" in lowered):
            return True
        return False
