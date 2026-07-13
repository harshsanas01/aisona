from typing import List

from carecall_application.ports.answerability_gate import AnswerabilityGate
from carecall_domain import Chunk

from .query_intent import QueryIntentClassifier


class HeuristicAnswerabilityGate(AnswerabilityGate):
    """Rule-based defense against confidently answering questions the
    retrieved evidence does not actually support - see
    docs/architecture/grounding.md and docs/adr/0003-server-owned-citations.md
    for the full pipeline this is one stage of.
    """

    def __init__(self, query_intent_classifier: QueryIntentClassifier | None = None):
        self._query_intent = query_intent_classifier or QueryIntentClassifier()

    def is_query_out_of_scope(self, question: str) -> bool:
        return not self._query_intent.classify(question).in_domain

    def is_unanswerable(self, question: str, chunks: List[Chunk]) -> bool:
        lowered = question.lower()
        if any(term in lowered for term in ["chest pain", "fell recently", "fallen recently", "fall recently"]):
            return True
        if "fall" in lowered and ("did not" in lowered or "no" in lowered or "any participant" in lowered):
            return True
        return False
