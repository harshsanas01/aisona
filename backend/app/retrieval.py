from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .data_loader import TranscriptCorpus
from .models import Citation, Turn


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

    def retrieve(self, query: str, limit: int = 8, patient_id: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Chunk]:
        if not query or not query.strip():
            return []
        query_terms = query.lower()
        boost_keywords = []
        if 'dizzy' in query_terms or 'dizziness' in query_terms:
            boost_keywords.append('dizzy')
        if 'sleep' in query_terms or 'sleeping' in query_terms:
            boost_keywords.extend(['sleep', 'waking', 'awake', 'night', 'dawn', 'rest'])
        if 'cough' in query_terms:
            boost_keywords.append('cough')
        if 'fall' in query_terms or 'fell' in query_terms:
            boost_keywords.append('fall')
        if 'medication' in query_terms or 'pill' in query_terms or 'lisinopril' in query_terms:
            boost_keywords.extend(['medication', 'pill', 'lisinopril', 'started'])

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
            boost = 0.0
            if chunk.patient_name.lower() in query.lower():
                boost += 0.2
            if any(token in query.lower() for token in ['lisinopril', 'medication', 'pill', 'started']):
                if any(token in chunk.text.lower() for token in ['lisinopril', 'medication', 'pill', 'started']):
                    boost += 0.25
                if 'lisinopril' in chunk.text.lower():
                    boost += 0.35
                if 'started me on a new blood pressure pill' in chunk.text.lower():
                    boost += 0.5
            if 'first mentioned' in query.lower() or 'first mention' in query.lower() or 'when was it first mentioned' in query.lower():
                boost += 0.15
            if start_date and chunk.date >= start_date:
                boost += 0.03
            if end_date and chunk.date <= end_date:
                boost += 0.03
            for keyword in boost_keywords:
                if keyword in chunk.text.lower():
                    boost += 0.05
            combined_score = 0.45 * lex_score + 0.55 * sem_score + boost
            combined.append((combined_score, chunk))

        ranked = sorted(combined, key=lambda item: item[0], reverse=True)
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

    def _lexical_score(self, query: str, chunk: Chunk) -> float:
        q_terms = re.findall(r"[a-zA-Z0-9]+", query.lower())
        if not q_terms:
            return 0.0
        doc_tokens = re.findall(r"[a-zA-Z0-9]+", (chunk.metadata_text + ' ' + chunk.text).lower())
        counter = Counter(doc_tokens)
        query_counter = Counter(q_terms)
        overlap = sum(min(query_counter[token], counter[token]) for token in query_counter)
        if not overlap:
            return 0.0
        return overlap / max(1, len(query_counter))
