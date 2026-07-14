from typing import List, Optional

from carecall_domain import DateRange
from carecall_retrieval import HybridRetriever, IdentityReranker, KeywordOverlapReranker

from ..dto.retrieval_comparison import RetrievalModeCandidate, RetrievalModeResult
from ..ports.repositories import ChunkRepository


class CompareRetrievalModesUseCase:
    """Developer-only tool (Retrieval Comparison Lab): runs one question
    through four retrieval configurations - lexical-only, semantic-only,
    hybrid (production weights), and hybrid+rerank - built fresh from the
    current chunk corpus on every call, so the comparison always reflects
    whatever calls have actually been ingested. Never touches the live,
    production-tuned retrieval_service used by /api/ask - a mis-tuned
    comparison run can never affect real answers."""

    def __init__(
        self,
        chunk_repository: ChunkRepository,
        *,
        lexical_weight: float,
        semantic_weight: float,
        min_relevance_score: float,
        default_top_k: int,
    ):
        self.chunk_repository = chunk_repository
        self.lexical_weight = lexical_weight
        self.semantic_weight = semantic_weight
        self.min_relevance_score = min_relevance_score
        self.default_top_k = default_top_k

    def execute(
        self,
        question: str,
        *,
        patient_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[RetrievalModeResult]:
        chunks = self.chunk_repository.all_chunks()
        date_range = DateRange(start=start_date, end=end_date)
        top_k = limit or self.default_top_k

        mode_configs = [
            ("lexical", 1.0, 0.0, False),
            ("semantic", 0.0, 1.0, False),
            ("hybrid", self.lexical_weight, self.semantic_weight, False),
            ("hybrid_rerank", self.lexical_weight, self.semantic_weight, True),
        ]

        results: List[RetrievalModeResult] = []
        for mode, lex_weight, sem_weight, use_rerank in mode_configs:
            retriever = HybridRetriever(
                chunks,
                lexical_weight=lex_weight,
                semantic_weight=sem_weight,
                min_relevance_score=self.min_relevance_score,
                default_top_k=top_k,
                reranker=KeywordOverlapReranker() if use_rerank else IdentityReranker(),
            )
            scored = retriever.retrieve_with_scores(
                question, limit=top_k, patient_id=patient_id, date_range=date_range,
            )
            candidates = [
                RetrievalModeCandidate(
                    chunk_id=chunk.chunk_id,
                    call_id=chunk.call_id,
                    patient_id=chunk.patient_id,
                    patient_name=chunk.patient_name,
                    date=chunk.date,
                    turn_start=chunk.turn_start,
                    turn_end=chunk.turn_end,
                    quote=chunk.text[:220],
                    score=round(score, 4),
                )
                for score, chunk in scored
            ]
            results.append(RetrievalModeResult(
                mode=mode,
                lexical_weight=lex_weight,
                semantic_weight=sem_weight,
                reranked=use_rerank,
                candidates=candidates,
            ))
        return results
