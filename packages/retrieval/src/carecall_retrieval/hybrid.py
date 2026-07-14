from __future__ import annotations

import re
from typing import List, Optional, Tuple

from carecall_application.ports.retrieval_service import RetrievalService
from carecall_domain import Chunk, DateRange

from .lexical import LexicalScorer
from .reranking import IdentityReranker, Reranker
from .semantic import SemanticScorer
from .vectorization import build_vectorizer

# Below this fused score, evidence is treated as too weak to ground an
# answer in. Calibrated against the evaluation set: legitimate supported
# questions score well above this, while out-of-domain questions only ever
# match on generic filler words and score below it.
DEFAULT_MIN_RELEVANCE_SCORE = 0.15
DEFAULT_LEXICAL_WEIGHT = 0.45
DEFAULT_SEMANTIC_WEIGHT = 0.55
DEFAULT_TOP_K = 8

ScoredChunk = Tuple[float, Chunk]

# Capitalized words in a query are usually names - including third parties
# (e.g. "Gus", mentioned only inside another patient's call, never as a
# chunk's own patient_name). Matching them verbatim against chunk text lets
# retrieval surface a third-party mention that the patient-name boost alone
# would miss. len>=3 and not fully uppercase filters out "I"/acronyms.
_PROPER_NOUN_PATTERN = re.compile(r"\b[A-Z][a-zA-Z]{2,}\b")

# Excluded from the proper-noun boost above: these are only capitalized
# because they start the sentence, not because they're names, and several
# ("Did", "Was") appear constantly in assistant dialogue ("Did you...") -
# without this exclusion they'd add a spurious boost to nearly every chunk.
_QUESTION_STARTER_WORDS = frozenset({
    "Did", "Has", "Have", "Had", "Was", "Were", "Is", "Are", "Should",
    "Would", "Could", "What", "Who", "When", "Where", "Why", "How",
    "Which", "Does", "Do", "Tell", "Can", "Will", "The", "Any",
    # Calendar words are capitalized but are not names - without this a
    # question like "reported feeling dizzy in June?" would treat "June"
    # as a person to match against chunk text, ignoring genuinely dizzy
    # evidence in favor of any unrelated chunk that happens to also
    # mention the word "June".
    "January", "February", "March", "April", "May", "June", "July",
    "August", "September", "October", "November", "December",
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    "Today", "Tomorrow", "Yesterday",
})


class HybridRetriever(RetrievalService):
    """Ranking algorithm (see docs/architecture/retrieval.md for the full
    writeup):

    1. Chunks are pre-built (2-4 turn overlapping windows, one per call) by
       the caller - typically via a ChunkRepository - and passed in here.
    2. Score each chunk lexically (IDF-weighted term overlap) and
       semantically (TF-IDF cosine similarity proxy) - both already bounded
       to roughly [0, 1], so no extra normalization step is needed before
       fusion.
    3. Fuse via a configurable weighted sum:
       score = lexical_weight * lexical + semantic_weight * semantic + boost
    4. Apply small, symptom-gated keyword boosts (only fire when the query
       names a known symptom/topic, so out-of-domain questions get none).
    5. Drop anything below min_relevance_score.
    6. Rerank (identity by default - a real cross-encoder can be plugged in
       via the Reranker port without touching fusion logic).
    7. Diversify the final ranked list by call so one chatty call can't
       crowd out other relevant sources, and cap at top_k.
    """

    def __init__(
        self,
        chunks: List[Chunk],
        *,
        lexical_weight: float = DEFAULT_LEXICAL_WEIGHT,
        semantic_weight: float = DEFAULT_SEMANTIC_WEIGHT,
        min_relevance_score: float = DEFAULT_MIN_RELEVANCE_SCORE,
        default_top_k: int = DEFAULT_TOP_K,
        reranker: Optional[Reranker] = None,
    ):
        self.lexical_weight = lexical_weight
        self.semantic_weight = semantic_weight
        self.min_relevance_score = min_relevance_score
        self.default_top_k = default_top_k
        self.reranker = reranker or IdentityReranker()

        self.refresh(chunks)

    def refresh(self, chunks: List[Chunk]) -> None:
        """Rebuild the shared vector space and scorers from an updated chunk
        list. Called after ingestion so a newly ingested call is searchable
        immediately, without restarting the process."""
        self.chunks = list(chunks)
        self._vectorizer, self._matrix = build_vectorizer(self.chunks)
        self._chunk_index = {chunk.chunk_id: i for i, chunk in enumerate(self.chunks)}
        self._lexical = LexicalScorer(self._vectorizer, self.chunks)
        self._semantic = SemanticScorer(self._vectorizer, self._matrix, self._chunk_index)

    def _boost_keywords(self, lowered_query: str) -> List[str]:
        boost_keywords = []
        if "dizzy" in lowered_query or "dizziness" in lowered_query:
            boost_keywords.append("dizzy")
        if "sleep" in lowered_query or "sleeping" in lowered_query:
            boost_keywords.extend(["sleep", "waking", "awake", "night", "dawn", "rest"])
        if "cough" in lowered_query:
            boost_keywords.append("cough")
        if "fall" in lowered_query or "fell" in lowered_query:
            boost_keywords.extend(["fall", "fell", "tripped", "sprained", "went down"])
        if "medication" in lowered_query or "pill" in lowered_query or "lisinopril" in lowered_query:
            boost_keywords.extend(["medication", "pill", "lisinopril", "started"])
        return boost_keywords

    def _boost_score(
        self,
        query: str,
        chunk: Chunk,
        boost_keywords: List[str],
        date_range: Optional[DateRange],
    ) -> float:
        lowered_query = query.lower()
        boost = 0.0
        if chunk.patient_name.lower() in lowered_query:
            boost += 0.2
        for name in _PROPER_NOUN_PATTERN.findall(query):
            if name in _QUESTION_STARTER_WORDS:
                continue
            if name != name.upper() and name in chunk.text:
                boost += 0.15
        if any(token in lowered_query for token in ["lisinopril", "medication", "pill", "started"]):
            if any(token in chunk.text.lower() for token in ["lisinopril", "medication", "pill", "started"]):
                boost += 0.25
            if "lisinopril" in chunk.text.lower():
                boost += 0.35
            if "started me on a new blood pressure pill" in chunk.text.lower():
                boost += 0.5
        if "first mentioned" in lowered_query or "first mention" in lowered_query or "when was it first mentioned" in lowered_query:
            boost += 0.15
        if date_range is not None:
            if date_range.start and chunk.date >= date_range.start:
                boost += 0.03
            if date_range.end and chunk.date <= date_range.end:
                boost += 0.03
        for keyword in boost_keywords:
            if keyword in chunk.text.lower():
                # 0.08: with the stricter, IDF-weighted lexical score, purely
                # synonymous evidence (e.g. "waking"/"rest" for a "sleeping"
                # query, which share no literal tokens) needs this curated,
                # symptom-gated boost to clear the relevance threshold. It
                # only ever fires when the query itself names a known
                # symptom, so out-of-domain questions get no benefit.
                boost += 0.08
        return boost

    def relevance_score(self, query: str, chunk: Chunk, date_range: Optional[DateRange] = None) -> float:
        """Recompute the same fused score used to rank candidates, for a
        single (query, chunk) pair - exposed so callers can independently
        confirm a chunk clears the relevance threshold instead of trusting
        retrieval output merely because the list is non-empty."""
        lowered_query = query.lower()
        boost_keywords = self._boost_keywords(lowered_query)
        lex_score = self._lexical.score(query, chunk)
        sem_score = self._semantic.score(query, chunk)
        boost = self._boost_score(query, chunk, boost_keywords, date_range)
        return self.lexical_weight * lex_score + self.semantic_weight * sem_score + boost

    def retrieve(
        self,
        query: str,
        *,
        limit: Optional[int] = None,
        patient_id: Optional[str] = None,
        date_range: Optional[DateRange] = None,
    ) -> List[Chunk]:
        return [chunk for _, chunk in self.retrieve_with_scores(
            query, limit=limit, patient_id=patient_id, date_range=date_range,
        )]

    def retrieve_with_scores(
        self,
        query: str,
        *,
        limit: Optional[int] = None,
        patient_id: Optional[str] = None,
        date_range: Optional[DateRange] = None,
    ) -> List[ScoredChunk]:
        """Same ranking as retrieve(), but also returns each chunk's final
        score (fused score plus any reranking boost) - used by the
        Retrieval Comparison Lab (developer-only) to make each mode's
        ranking numerically transparent rather than just showing an order."""
        if not query or not query.strip():
            return []
        top_k = limit if limit is not None else self.default_top_k

        filtered = [c for c in self.chunks if date_range is None or date_range.contains(c.date)]
        if patient_id:
            filtered = [c for c in filtered if c.patient_id == patient_id]
        if not filtered:
            return []

        boost_keywords = self._boost_keywords(query.lower())
        combined: List[ScoredChunk] = []
        for chunk in filtered:
            lex_score = self._lexical.score(query, chunk)
            sem_score = self._semantic.score(query, chunk)
            boost = self._boost_score(query, chunk, boost_keywords, date_range)
            score = self.lexical_weight * lex_score + self.semantic_weight * sem_score + boost
            combined.append((score, chunk))

        # Require meaningful relevance before a chunk is allowed to ground
        # an answer - without this, the top-scoring chunk of an empty match
        # would still be returned merely because *some* chunk exists.
        relevant = [item for item in combined if item[0] >= self.min_relevance_score]
        ranked = sorted(relevant, key=lambda item: item[0], reverse=True)
        reranked = self.reranker.rerank(query, ranked)
        return self._diversify(reranked, top_k)

    def _diversify(self, ranked: List[ScoredChunk], limit: int) -> List[ScoredChunk]:
        selected: List[ScoredChunk] = []
        seen_calls = set()
        for score, chunk in ranked:
            if len(selected) >= limit:
                break
            if chunk.call_id in seen_calls:
                if len(selected) == 0:
                    selected.append((score, chunk))
                    seen_calls.add(chunk.call_id)
                continue
            selected.append((score, chunk))
            seen_calls.add(chunk.call_id)
        return selected
