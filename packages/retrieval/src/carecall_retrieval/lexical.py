from __future__ import annotations

import re
from collections import Counter
from typing import List

from carecall_domain import Chunk
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

# Query terms shorter than this or in the stopword list are dropped before
# lexical scoring so that filler words can't manufacture false overlap.
_MIN_TERM_LENGTH = 3

# sklearn's ENGLISH_STOP_WORDS lemmatizes some auxiliary verbs ("has", "had")
# but misses their gerund forms, which show up constantly in natural-language
# questions ("having", "doing") without carrying any topical content.
_EXTRA_STOP_WORDS = frozenset({"having", "doing", "being", "getting", "going"})
_STOP_WORDS = ENGLISH_STOP_WORDS | _EXTRA_STOP_WORDS

# Terms that show up in more than this fraction of chunks behave like
# corpus-specific filler (e.g. "today", used in almost every call's
# greeting) rather than evidence, so they're excluded from lexical scoring
# entirely - otherwise a coincidental match on them could make an unrelated
# question look grounded.
_COMMON_TERM_DOC_FREQ_RATIO = 0.12

# Word regex that keeps contractions/possessives intact ("won't", "today's")
# as single tokens instead of splitting on the apostrophe. Splitting them
# (the naive `\w+` behavior) turns "won't" into the free-floating token
# "won", which can spuriously match an unrelated query like "Who won the
# Super Bowl?" even though the transcript never discusses winning anything.
_TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9]+(?:'[a-zA-Z]+)?")


def tokenize(text: str) -> List[str]:
    # Possessives normalize to their base noun ("today's" -> "today") since
    # they refer to the same entity, letting document-frequency filtering
    # catch "today's" as the same generic filler as bare "today". Negative
    # contractions ("won't", "isn't") are left intact - merging "won't" into
    # "won" would create a false match, since it means the opposite.
    tokens = _TOKEN_PATTERN.findall(text.lower())
    return [t[:-2] if t.endswith("'s") else t for t in tokens]


class LexicalScorer:
    """IDF-weighted lexical overlap between a query and a chunk, using the
    vocabulary/IDF weights of a TF-IDF vectorizer already fit over the
    corpus (shared with the semantic scorer so both operate in the same
    vector space)."""

    def __init__(self, vectorizer, chunks: List[Chunk]):
        self._vectorizer = vectorizer
        self._doc_frequency = self._compute_doc_frequency(chunks)
        self._chunk_count = max(1, len(chunks))

    @staticmethod
    def _compute_doc_frequency(chunks: List[Chunk]) -> Counter:
        doc_frequency: Counter = Counter()
        for chunk in chunks:
            tokens = set(tokenize(chunk.metadata_text + " " + chunk.text))
            doc_frequency.update(tokens)
        return doc_frequency

    def _meaningful_query_terms(self, query: str) -> List[str]:
        terms = tokenize(query)
        meaningful = []
        for term in terms:
            if len(term) < _MIN_TERM_LENGTH or term in _STOP_WORDS:
                continue
            doc_freq_ratio = self._doc_frequency.get(term, 0) / self._chunk_count
            if doc_freq_ratio > _COMMON_TERM_DOC_FREQ_RATIO:
                continue
            meaningful.append(term)
        return meaningful

    def score(self, query: str, chunk: Chunk) -> float:
        q_terms = self._meaningful_query_terms(query)
        if not q_terms:
            return 0.0
        doc_tokens = set(tokenize(chunk.metadata_text + " " + chunk.text))
        vocabulary = self._vectorizer.vocabulary_
        idf = self._vectorizer.idf_
        max_idf = float(idf.max())

        # Weight each matched term by its corpus rarity (IDF) so rare,
        # discriminating terms (e.g. "lisinopril", "dizzy") dominate the
        # overlap score. Generic filler words never reach here - they're
        # dropped by _meaningful_query_terms. A term absent from the corpus
        # vocabulary entirely is treated as maximally rare.
        total_weight = 0.0
        matched_weight = 0.0
        for term in set(q_terms):
            weight = float(idf[vocabulary[term]]) if term in vocabulary else max_idf
            total_weight += weight
            if term in doc_tokens:
                matched_weight += weight
        if total_weight == 0.0 or matched_weight == 0.0:
            return 0.0
        return matched_weight / total_weight
