from typing import Iterator, List, Optional

from carecall_domain import Chunk, DateRange

from ..dto.ask_result import AskQuestionResult
from ..dto.stream_event import StreamEvent
from ..ports.answer_generator import AnswerGenerator
from ..ports.answerability_gate import AnswerabilityGate
from ..ports.citation_validator import CitationValidator
from ..ports.retrieval_service import RetrievalService
from ..ports.support_validator import SupportValidator

UNANSWERABLE_MESSAGE = (
    "The care-call transcripts do not contain enough evidence to answer this question."
)


class AskQuestionUseCase:
    """Orchestrates the grounded question-answering flow (see
    docs/architecture/grounding.md for the full 11-step pipeline this
    implements):

    1. Validate filters (DateRange raises if start_date is after end_date).
    2. Query validation / scope classification - reject out-of-domain and
       medical-advice-seeking questions before spending a retrieval call.
    3-6. Retrieve candidate evidence (already applies metadata filters, a
       minimum relevance threshold, and evidence diversification by call).
    7. Run the answerability gate - if evidence is empty or judged
       insufficient, short-circuit to an unanswerable result WITHOUT ever
       calling the answer generator.
    8. Generate a grounded answer from the evidence.
    9. Validate the generator's claimed evidence ids against what was
       actually retrieved - a generator can never inject a call id, patient
       id, turn number, quote, or date that doesn't already exist in the
       retrieved evidence.
    10. Post-generation support validation - does the selected evidence
        plausibly relate to this question at all (catches generation
        drifting onto an unrelated call).
    11. Reconstruct and structurally validate citations, then return.
    """

    def __init__(
        self,
        retrieval_service: RetrievalService,
        answer_generator: AnswerGenerator,
        answerability_gate: AnswerabilityGate,
        support_validator: SupportValidator,
        citation_validator: CitationValidator,
        default_limit: int = 8,
    ):
        self.retrieval_service = retrieval_service
        self.answer_generator = answer_generator
        self.answerability_gate = answerability_gate
        self.support_validator = support_validator
        self.citation_validator = citation_validator
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
        filters = {"patient_id": patient_id, "start_date": start_date, "end_date": end_date}

        if self.answerability_gate.is_query_out_of_scope(question):
            return self._unanswerable(
                question, 0, filters, grounding_checks={"out_of_scope": True},
            )

        chunks = self.retrieval_service.retrieve(
            question, limit=self.default_limit, patient_id=patient_id, date_range=date_range,
        )
        candidate_chunk_ids = [c.chunk_id for c in chunks]

        if not chunks or self.answerability_gate.is_unanswerable(question, chunks):
            return self._unanswerable(
                question, len(chunks), filters, candidate_chunk_ids=candidate_chunk_ids,
                grounding_checks={"answerability_gate": False},
            )

        grounded = self.answer_generator.generate(question, chunks, filters=filters)
        if not grounded.answerable:
            return self._unanswerable(
                question, len(chunks), filters, candidate_chunk_ids=candidate_chunk_ids,
                model_name=grounded.model_name, prompt_version=grounded.prompt_version, usage=grounded.usage,
                fallback_used=grounded.used_fallback, grounding_checks={"generator_answerable": False},
            )

        selected_chunks = self._select_evidence(chunks, grounded.used_evidence_ids)

        if not self.support_validator.is_supported(question, selected_chunks):
            return self._unanswerable(
                question, len(chunks), filters, candidate_chunk_ids=candidate_chunk_ids,
                selected_evidence_ids=[c.chunk_id for c in selected_chunks],
                model_name=grounded.model_name, prompt_version=grounded.prompt_version, usage=grounded.usage,
                fallback_used=grounded.used_fallback, grounding_checks={"support_validation": False},
            )

        citations = self.citation_validator.validate([
            chunk.to_citation(quote=self._quote_from_chunk(chunk)) for chunk in selected_chunks
        ])
        if not citations:
            return self._unanswerable(
                question, len(chunks), filters, candidate_chunk_ids=candidate_chunk_ids,
                selected_evidence_ids=[c.chunk_id for c in selected_chunks],
                model_name=grounded.model_name, prompt_version=grounded.prompt_version, usage=grounded.usage,
                fallback_used=grounded.used_fallback, grounding_checks={"citation_validation": False},
            )

        return AskQuestionResult(
            question=question,
            answer=grounded.answer,
            answerable=True,
            confidence=grounded.confidence,
            citations=citations,
            retrieval_debug={"mode": "hybrid", "candidate_count": len(chunks)},
            filters=filters,
            candidate_chunk_ids=candidate_chunk_ids,
            selected_evidence_ids=[c.chunk_id for c in selected_chunks],
            model_name=grounded.model_name,
            prompt_version=grounded.prompt_version,
            usage=grounded.usage,
            fallback_used=grounded.used_fallback,
            grounding_checks={
                "answerability_gate": True, "generator_answerable": True,
                "support_validation": True, "citation_validation": True,
            },
        )

    def stream(
        self,
        question: str,
        *,
        patient_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Iterator[StreamEvent]:
        """Same grounding flow as execute(), emitted as a sequence of events
        instead of a single result, for the SSE endpoint. Citations are only
        ever yielded in the 'citations' event, built from the same
        server-owned chunk metadata as execute() - never streamed from the
        generator directly, and never before generation has completed and
        been validated.

        Note: this streams the already-fully-generated, already-validated
        answer text progressively (word by word) rather than raw tokens
        from the LLM provider - AnswerGenerator.generate() returns a
        complete GroundedAnswer synchronously today. A token-streaming
        provider would plug in without changing this contract.
        """
        date_range = DateRange(start=start_date, end=end_date)  # may raise InvalidDateRangeError - before any event
        filters = {"patient_id": patient_id, "start_date": start_date, "end_date": end_date}

        if self.answerability_gate.is_query_out_of_scope(question):
            yield StreamEvent("retrieval_started")
            yield StreamEvent("retrieval_completed", {"candidate_count": 0})
            yield from self._stream_unanswerable(filters)
            return

        yield StreamEvent("retrieval_started")

        chunks = self.retrieval_service.retrieve(
            question, limit=self.default_limit, patient_id=patient_id, date_range=date_range,
        )
        yield StreamEvent("retrieval_completed", {"candidate_count": len(chunks)})

        if not chunks or self.answerability_gate.is_unanswerable(question, chunks):
            yield from self._stream_unanswerable(filters)
            return

        grounded = self.answer_generator.generate(question, chunks, filters=filters)
        if not grounded.answerable:
            yield from self._stream_unanswerable(filters)
            return

        selected_chunks = self._select_evidence(chunks, grounded.used_evidence_ids)

        if not self.support_validator.is_supported(question, selected_chunks):
            yield from self._stream_unanswerable(filters)
            return

        citations = self.citation_validator.validate([
            chunk.to_citation(quote=self._quote_from_chunk(chunk)) for chunk in selected_chunks
        ])
        if not citations:
            yield from self._stream_unanswerable(filters)
            return

        for word in grounded.answer.split(" "):
            yield StreamEvent("answer_delta", {"text": word + " "})

        yield StreamEvent("citations", {"citations": citations})
        yield StreamEvent("completed", {"answerable": True, "confidence": grounded.confidence, "filters": filters})

    def _select_evidence(self, chunks: List[Chunk], used_evidence_ids: List[str]) -> List[Chunk]:
        chunk_lookup = {chunk.chunk_id: chunk for chunk in chunks}
        valid_ids = [eid for eid in used_evidence_ids if eid in chunk_lookup]
        if not valid_ids:
            valid_ids = [chunk.chunk_id for chunk in chunks[:3]]
        return [chunk_lookup[eid] for eid in valid_ids[:3]]

    def _stream_unanswerable(self, filters: dict) -> Iterator[StreamEvent]:
        yield StreamEvent("answer_delta", {"text": UNANSWERABLE_MESSAGE})
        yield StreamEvent("citations", {"citations": []})
        yield StreamEvent("completed", {"answerable": False, "confidence": "low", "filters": filters})

    @staticmethod
    def _quote_from_chunk(chunk: Chunk) -> str:
        turns_text = [f"{turn.speaker}: {turn.text}" for turn in chunk.turns]
        return " | ".join(turns_text)[:220]

    def _unanswerable(
        self,
        question: str,
        candidate_count: int,
        filters: dict,
        *,
        candidate_chunk_ids: Optional[List[str]] = None,
        selected_evidence_ids: Optional[List[str]] = None,
        model_name: Optional[str] = None,
        prompt_version: str = "v1",
        usage: Optional[dict] = None,
        fallback_used: bool = False,
        grounding_checks: Optional[dict] = None,
    ) -> AskQuestionResult:
        return AskQuestionResult(
            question=question,
            answer=UNANSWERABLE_MESSAGE,
            answerable=False,
            confidence="low",
            citations=[],
            retrieval_debug={"mode": "hybrid", "candidate_count": candidate_count},
            filters=filters,
            candidate_chunk_ids=candidate_chunk_ids or [],
            selected_evidence_ids=selected_evidence_ids or [],
            model_name=model_name,
            prompt_version=prompt_version,
            usage=usage,
            fallback_used=fallback_used,
            grounding_checks=grounding_checks or {},
        )
