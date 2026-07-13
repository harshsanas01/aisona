from typing import List

from carecall_application.dto.answer import GroundedAnswer
from carecall_application.ports.answer_generator import AnswerGenerator
from carecall_domain import Chunk

UNANSWERABLE_MESSAGE = "I do not have enough evidence in the transcript corpus to answer that confidently."


class MockAnswerGenerator(AnswerGenerator):
    """Deterministic, offline answer generator. No network calls, no API
    key required - this is what keeps the demo mode fully self-contained."""

    def generate(self, question: str, evidence: List[Chunk], filters: dict) -> GroundedAnswer:
        if not evidence:
            return GroundedAnswer(answerable=False, answer=UNANSWERABLE_MESSAGE, used_evidence_ids=[], confidence="low")

        text = self._mock_answer(question, evidence)
        used_ids = [chunk.chunk_id for chunk in evidence[:3]]
        return GroundedAnswer(answerable=True, answer=text, used_evidence_ids=used_ids, confidence="high", model_name="mock")

    @staticmethod
    def _mock_answer(question: str, chunks: List[Chunk]) -> str:
        best = chunks[0]
        lowered = question.lower()
        if "lisinopril" in lowered:
            return "Margaret Chen started lisinopril, which was first mentioned in call_003."
        if "dizzy" in lowered or "dizziness" in lowered:
            return f"{best.patient_name} described dizziness in the retrieved evidence."
        if "sleep" in lowered or "rest" in lowered:
            return f"{best.patient_name} mentioned sleep-related concerns in the retrieved evidence."
        if "cough" in lowered:
            return f"{best.patient_name} discussed a cough in the retrieved evidence."
        if "fall" in lowered:
            return "The corpus does not establish that a participant recently fell."
        if "van" in lowered:
            return "Frank Delgado described frustration with the van service being late."
        if "knee" in lowered:
            return "Rosa Kim said her knee had been aching on stairs."
        return best.turns[-1].text
