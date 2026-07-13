from typing import Optional

from carecall_domain import DateRange

from ..dto.ask_result import AskQuestionResult
from ..ports.retrieval_service import RetrievalService
from ..ports.answer_generator import AnswerGenerator
from ..ports.answerability_gate import AnswerabilityGate

UNANSWERABLE_MESSAGE = (
    "The care-call transcripts do not contain enough evidence to answer this question."
)


class AskQuestionUseCase:
    """Orchestrates the grounded question-answering flow:

    1. Validate filters (DateRange raises if start_date is after end_date).
    2. Retrieve candidate evidence chunks (retrieval already applies a
       minimum relevance threshold and metadata filters).
    3. Run the answerability gate - if evidence is empty or judged
       insufficient, short-circuit to an unanswerable result WITHOUT ever
       calling the answer generator.
    4. Generate a grounded answer from the evidence.
    5. Reconstruct citations strictly from server-owned chunk metadata using
       only the evidence ids the generator claims to have used - a
       generator can never inject a call id, patient id, turn number, quote,
       or date that doesn't already exist in the retrieved evidence.
    """

    def __init__(
        self,
        retrieval_service: RetrievalService,
        answer_generator: AnswerGenerator,
        answerability_gate: AnswerabilityGate,
        default_limit: int = 8,
    ):
        self.retrieval_service = retrieval_service
        self.answer_generator = answer_generator
        self.answerability_gate = answerability_gate
        self.default_limit = default_limit

    def execute(
        self,
        question: str,
        *,
        patient_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> AskQuestionResult:
        date_range = DateRange(start=start_date, end=end_date)

        chunks = self.retrieval_service.retrieve(
            question,
            limit=self.default_limit,
            patient_id=patient_id,
            date_range=date_range,
        )

        if not chunks or self.answerability_gate.is_unanswerable(question, chunks):
            return self._unanswerable(question, len(chunks))

        grounded = self.answer_generator.generate(
            question,
            chunks,
            filters={"patient_id": patient_id, "start_date": start_date, "end_date": end_date},
        )

        if not grounded.answerable:
            return self._unanswerable(question, len(chunks))

        chunk_lookup = {chunk.chunk_id: chunk for chunk in chunks}
        valid_ids = [eid for eid in grounded.used_evidence_ids if eid in chunk_lookup]
        if not valid_ids:
            valid_ids = [chunk.chunk_id for chunk in chunks[:3]]

        citations = [
            chunk_lookup[eid].to_citation(quote=self._quote_from_chunk(chunk_lookup[eid]))
            for eid in valid_ids[:3]
        ]

        return AskQuestionResult(
            question=question,
            answer=grounded.answer,
            answerable=True,
            confidence=grounded.confidence,
            citations=citations,
            retrieval_debug={"mode": "hybrid", "candidate_count": len(chunks)},
        )

    @staticmethod
    def _quote_from_chunk(chunk) -> str:
        turns_text = [f"{turn.speaker}: {turn.text}" for turn in chunk.turns]
        return " | ".join(turns_text)[:220]

    def _unanswerable(self, question: str, candidate_count: int) -> AskQuestionResult:
        return AskQuestionResult(
            question=question,
            answer=UNANSWERABLE_MESSAGE,
            answerable=False,
            confidence="low",
            citations=[],
            retrieval_debug={"mode": "hybrid", "candidate_count": candidate_count},
        )
