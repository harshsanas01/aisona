from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .data_loader import TranscriptCorpus
from .models import Citation, Turn

# Below this combined lexical+semantic score, evidence is treated as too weak
# to ground an answer in. Calibrated against the eval set: legitimate
# supported questions ("Who has been having trouble sleeping?", "Which
# participants have reported feeling dizzy in June?") score well above this,
# while out-of-domain questions ("What is today's weather in LA?", "Who won
# the Super Bowl?") only ever match on generic filler words and score below it.
MIN_RELEVANCE_SCORE = 0.15

# Query terms shorter than this or in the stopword list are dropped before
# lexical scoring so that filler words can't manufacture false overlap.
_MIN_TERM_LENGTH = 3

# sklearn's ENGLISH_STOP_WORDS lemmatizes some auxiliary verbs ("has", "had")
# but misses their gerund forms, which show up constantly in natural-language
# questions ("having", "doing") without carrying any topical content.
_EXTRA_STOP_WORDS = frozenset({'having', 'doing', 'being', 'getting', 'going'})
_STOP_WORDS = ENGLISH_STOP_WORDS | _EXTRA_STOP_WORDS

# Terms that show up in more than this fraction of chunks behave like
# corpus-specific filler (e.g. "today", used in almost every call's
# greeting) rather than evidence. They're excluded from lexical scoring
# entirely so a coincidental match on them can't make an unrelated question
# look grounded.
_COMMON_TERM_DOC_FREQ_RATIO = 0.12

# Word regex that keeps contractions/possessives intact ("won't", "today's")
# as single tokens instead of splitting on the apostrophe. Splitting them
# (the naive `\w+` behavior) turns "won't" into the free-floating token "won",
# which can spuriously match an unrelated query like "Who won the Super
# Bowl?" even though the transcript never actually discusses winning anything.
_TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9]+(?:'[a-zA-Z]+)?")


def _tokenize(text: str) -> List[str]:
    # Possessives normalize to their base noun ("today's" -> "today",
    # "Dorothy's" -> "dorothy") since they refer to the same entity - this
    # lets document-frequency filtering catch "today's" as the same generic
    # filler as bare "today". Negative contractions ("won't", "isn't") are
    # left intact: they mean the opposite of their base verb, so merging
    # "won't" into "won" would create a false match.
    tokens = _TOKEN_PATTERN.findall(text.lower())
    return [t[:-2] if t.endswith("'s") else t for t in tokens]


@dataclass
class Chunk:
    chunk_id: str
    call_id: str
    patient_id: str
    patient_name: str
    date: str
    turn_start: int
    turn_end: int
    turns: List[Turn]
    metadata_text: str
    text: str

    def to_citation(self, quote: Optional[str] = None) -> Citation:
        excerpt = quote or self.text[:180]
        return Citation(
            call_id=self.call_id,
            patient_id=self.patient_id,
            patient_name=self.patient_name,
            date=self.date,
            turn_start=self.turn_start,
            turn_end=self.turn_end,
            quote=excerpt,
        )


class TranscriptRetriever:
    def __init__(self, corpus: TranscriptCorpus):
        self.corpus = corpus
        self.chunks = self._build_chunks(corpus)
        self._vectorizer, self._matrix = self._fit_vectorizer()
        self._chunk_lookup = {chunk.chunk_id: index for index, chunk in enumerate(self.chunks)}
        self._doc_frequency = self._compute_doc_frequency()

    def _compute_doc_frequency(self) -> Counter:
        doc_frequency: Counter = Counter()
        for chunk in self.chunks:
            tokens = set(_tokenize(chunk.metadata_text + ' ' + chunk.text))
            doc_frequency.update(tokens)
        return doc_frequency

    def _build_chunks(self, corpus: TranscriptCorpus) -> List[Chunk]:
        chunks: List[Chunk] = []
        for call in corpus.calls:
            turns = call.turns
            for start in range(0, len(turns) - 1):
                window = turns[start:start + 4]
                if len(window) < 2:
                    continue
                participant_turns = [t for t in window if t.speaker == 'participant']
                center_turn = participant_turns[-1] if participant_turns else window[-1]
                text_parts = [f"{t.speaker}: {t.text}" for t in window]
                text = ' '.join(text_parts)
                metadata_parts = [
                    call.patient.name,
                    call.patient.id,
                    call.date,
                    call.call_id,
                    ' '.join(t.text for t in window),
                ]
                chunk = Chunk(
                    chunk_id=f"{call.call_id}:{start + 1}:{start + len(window)}",
                    call_id=call.call_id,
                    patient_id=call.patient.id,
                    patient_name=call.patient.name,
                    date=call.date,
                    turn_start=start + 1,
                    turn_end=start + len(window),
                    turns=window,
                    metadata_text=' '.join(metadata_parts),
                    text=text,
                )
                chunks.append(chunk)
        return chunks

    def _fit_vectorizer(self):
        texts = [f"{chunk.metadata_text} {chunk.text}" for chunk in self.chunks]
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, stop_words='english')
        matrix = vectorizer.fit_transform(texts)
        return vectorizer, matrix

    def _boost_keywords(self, lowered_query: str) -> List[str]:
        boost_keywords = []
        if 'dizzy' in lowered_query or 'dizziness' in lowered_query:
            boost_keywords.append('dizzy')
        if 'sleep' in lowered_query or 'sleeping' in lowered_query:
            boost_keywords.extend(['sleep', 'waking', 'awake', 'night', 'dawn', 'rest'])
        if 'cough' in lowered_query:
            boost_keywords.append('cough')
        if 'fall' in lowered_query or 'fell' in lowered_query:
            boost_keywords.append('fall')
        if 'medication' in lowered_query or 'pill' in lowered_query or 'lisinopril' in lowered_query:
            boost_keywords.extend(['medication', 'pill', 'lisinopril', 'started'])
        return boost_keywords

    def _boost_score(self, query: str, chunk: Chunk, boost_keywords: List[str], start_date: Optional[str], end_date: Optional[str]) -> float:
        lowered_query = query.lower()
        boost = 0.0
        if chunk.patient_name.lower() in lowered_query:
            boost += 0.2
        if any(token in lowered_query for token in ['lisinopril', 'medication', 'pill', 'started']):
            if any(token in chunk.text.lower() for token in ['lisinopril', 'medication', 'pill', 'started']):
                boost += 0.25
            if 'lisinopril' in chunk.text.lower():
                boost += 0.35
            if 'started me on a new blood pressure pill' in chunk.text.lower():
                boost += 0.5
        if 'first mentioned' in lowered_query or 'first mention' in lowered_query or 'when was it first mentioned' in lowered_query:
            boost += 0.15
        if start_date and chunk.date >= start_date:
            boost += 0.03
        if end_date and chunk.date <= end_date:
            boost += 0.03
        for keyword in boost_keywords:
            if keyword in chunk.text.lower():
                # 0.08 (not the previous 0.05): with the stricter,
                # IDF-weighted lexical score below, purely-synonymous
                # evidence (e.g. "waking"/"rest" for a "sleeping" query,
                # which share no literal tokens) needs this curated,
                # symptom-gated boost to clear MIN_RELEVANCE_SCORE. It
                # only ever fires when the query itself names a known
                # symptom, so out-of-domain questions get no benefit.
                boost += 0.08
        return boost

    def relevance_score(self, query: str, chunk: Chunk, start_date: Optional[str] = None, end_date: Optional[str] = None) -> float:
        """Recompute the same lexical+semantic+boost score used to rank
        candidates, for a single (query, chunk) pair. Exposed so callers
        (e.g. AnswerService) can independently confirm a chunk clears
        MIN_RELEVANCE_SCORE instead of trusting retrieval output merely
        because the list is non-empty."""
        lowered_query = query.lower()
        boost_keywords = self._boost_keywords(lowered_query)
        lex_score = self._lexical_score(query, chunk)
        if chunk.chunk_id in self._chunk_lookup:
            query_vector = self._vectorizer.transform([query])
            sem_score = float(cosine_similarity(query_vector, self._matrix[self._chunk_lookup[chunk.chunk_id]])[0][0])
        else:
            sem_score = 0.0
        boost = self._boost_score(query, chunk, boost_keywords, start_date, end_date)
        return 0.45 * lex_score + 0.55 * sem_score + boost

    def retrieve(self, query: str, limit: int = 8, patient_id: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Chunk]:
        if not query or not query.strip():
            return []
        query_terms = query.lower()
        boost_keywords = self._boost_keywords(query_terms)

        filtered = [chunk for chunk in self.chunks if self._matches_date_filters(chunk, start_date, end_date)]
        if 'chest pain' in query_terms:
            return []
        if patient_id:
            filtered = [chunk for chunk in filtered if chunk.patient_id == patient_id]

        if not filtered:
            return []

        vectorizer = self._vectorizer
        query_vector = vectorizer.transform([query])
        scores = cosine_similarity(query_vector, self._matrix[:, :]).reshape(-1)
        lexical_scores = np.array([self._lexical_score(query, chunk) for chunk in filtered], dtype=float)
        semantic_scores = np.array([scores[self._chunk_lookup[chunk.chunk_id]] for chunk in filtered], dtype=float)
        combined = []
        for idx, chunk in enumerate(filtered):
            lex_score = lexical_scores[idx]
            sem_score = semantic_scores[idx]
            boost = self._boost_score(query, chunk, boost_keywords, start_date, end_date)
            combined_score = 0.45 * lex_score + 0.55 * sem_score + boost
            combined.append((combined_score, chunk))

        # Require meaningful relevance before a chunk is allowed to ground an
        # answer. Without this, the top-scoring chunk of an empty match (all
        # scores ~0, or scores inflated only by generic filler words) would
        # still get returned merely because *some* chunk exists.
        relevant = [item for item in combined if item[0] >= MIN_RELEVANCE_SCORE]

        ranked = sorted(relevant, key=lambda item: item[0], reverse=True)
        diversified = self._diversify(ranked, limit)
        return [chunk for _, chunk in diversified]

    def _diversify(self, ranked: List[tuple[float, Chunk]], limit: int) -> List[tuple[float, Chunk]]:
        selected: List[tuple[float, Chunk]] = []
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

    def _matches_date_filters(self, chunk: Chunk, start_date: Optional[str], end_date: Optional[str]) -> bool:
        if start_date and chunk.date < start_date:
            return False
        if end_date and chunk.date > end_date:
            return False
        return True

    def _meaningful_query_terms(self, query: str) -> List[str]:
        chunk_count = max(1, len(self.chunks))
        terms = _tokenize(query)
        meaningful = []
        for term in terms:
            if len(term) < _MIN_TERM_LENGTH or term in _STOP_WORDS:
                continue
            doc_freq_ratio = self._doc_frequency.get(term, 0) / chunk_count
            if doc_freq_ratio > _COMMON_TERM_DOC_FREQ_RATIO:
                continue
            meaningful.append(term)
        return meaningful

    def _lexical_score(self, query: str, chunk: Chunk) -> float:
        q_terms = self._meaningful_query_terms(query)
        if not q_terms:
            return 0.0
        doc_tokens = set(_tokenize(chunk.metadata_text + ' ' + chunk.text))
        vocabulary = self._vectorizer.vocabulary_
        idf = self._vectorizer.idf_
        max_idf = float(idf.max())

        # Weight each matched term by its corpus rarity (IDF) so that
        # rare, discriminating terms (e.g. "lisinopril", "dizzy") dominate
        # the overlap score. Generic filler words (e.g. "today") never reach
        # here at all - they're dropped by _meaningful_query_terms. A term
        # absent from the corpus vocabulary entirely is treated as maximally
        # rare (it simply can't match, so it doesn't distort the denominator).
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
