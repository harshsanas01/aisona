from abc import ABC, abstractmethod
from typing import List, Tuple

from carecall_domain import Chunk

ScoredChunk = Tuple[float, Chunk]


class Reranker(ABC):
    """Optional post-fusion reranking stage. Kept as a real extension point:
    swap in a cross-encoder or LLM-based reranker without touching
    HybridRetriever's fusion/diversification logic."""

    @abstractmethod
    def rerank(self, query: str, scored_chunks: List[ScoredChunk]) -> List[ScoredChunk]: ...


class IdentityReranker(Reranker):
    """No-op reranker - the default. Fusion order is left unchanged."""

    def rerank(self, query: str, scored_chunks: List[ScoredChunk]) -> List[ScoredChunk]:
        return scored_chunks
