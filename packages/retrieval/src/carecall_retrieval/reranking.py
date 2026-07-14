import re
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


_WORD_PATTERN = re.compile(r"[a-z0-9']+")


def _words(text: str) -> List[str]:
    return _WORD_PATTERN.findall(text.lower())


def _ngrams(words: List[str], n: int) -> List[str]:
    return [" ".join(words[i:i + n]) for i in range(len(words) - n + 1)]


class KeywordOverlapReranker(Reranker):
    """Deterministic post-fusion reranker: boosts candidates that contain
    the query's exact multi-word phrases verbatim, not just overlapping
    individual tokens. Lexical/semantic scoring are both bag-of-words (or
    bag-of-words-proxy) methods that are blind to word order - two chunks
    that share the same words in a different order score identically to
    them. This is a genuine, explainable second-stage signal (the same
    intuition a cross-encoder captures, without requiring one): a chunk
    containing the literal phrase "started me on a new" is stronger
    evidence than one that merely contains "started", "new", and "me"
    somewhere unrelated in the text. Only reorders/re-scores candidates
    already present in scored_chunks - never adds or removes any."""

    def __init__(self, max_phrase_length: int = 4):
        self.max_phrase_length = max_phrase_length

    def _phrase_boost(self, query_words: List[str], chunk_text_lower: str) -> float:
        boost = 0.0
        for n in range(self.max_phrase_length, 1, -1):
            phrases = set(_ngrams(query_words, n))
            matches = sum(1 for phrase in phrases if phrase in chunk_text_lower)
            # Longer verbatim phrase matches are stronger evidence than
            # shorter ones - weight scales with phrase length.
            boost += matches * (0.05 * n)
        return boost

    def rerank(self, query: str, scored_chunks: List[ScoredChunk]) -> List[ScoredChunk]:
        query_words = _words(query)
        if not query_words:
            return scored_chunks
        rescored = [
            (score + self._phrase_boost(query_words, chunk.text.lower()), chunk)
            for score, chunk in scored_chunks
        ]
        # Stable sort: candidates with an equal rescored value keep their
        # original relative order rather than being shuffled.
        return sorted(rescored, key=lambda item: item[0], reverse=True)
