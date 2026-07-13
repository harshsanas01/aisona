from typing import Dict

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from carecall_domain import Chunk


class SemanticScorer:
    """Lightweight semantic similarity signal: cosine similarity between the
    query and chunk vectors in the same TF-IDF space used by LexicalScorer.

    This is a *proxy* for real semantic search, not a learned embedding - it
    still captures some paraphrase overlap via shared n-grams and rewards
    bigram context, but it will not generalize to true synonyms with zero
    lexical overlap. The EmbeddingProvider port (packages/persistence,
    production-like mode) is the real extension point for swapping this out
    for OpenAI or another embedding model without touching HybridRetriever.
    """

    def __init__(self, vectorizer, matrix, chunk_index: Dict[str, int]):
        self._vectorizer = vectorizer
        self._matrix = matrix
        self._chunk_index = chunk_index

    def score(self, query: str, chunk: Chunk) -> float:
        if chunk.chunk_id not in self._chunk_index:
            return 0.0
        query_vector = self._vectorizer.transform([query])
        row = self._chunk_index[chunk.chunk_id]
        return float(cosine_similarity(query_vector, self._matrix[row])[0][0])

    def score_all(self, query: str) -> np.ndarray:
        query_vector = self._vectorizer.transform([query])
        return cosine_similarity(query_vector, self._matrix).reshape(-1)
