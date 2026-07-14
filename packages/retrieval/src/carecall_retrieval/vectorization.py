from typing import Any, List, Tuple

from carecall_domain import Chunk
from sklearn.feature_extraction.text import TfidfVectorizer


def build_vectorizer(chunks: List[Chunk]) -> Tuple[TfidfVectorizer, Any]:
    """Fit a single shared TF-IDF vectorizer over the corpus. Both the
    lexical scorer (IDF-weighted term overlap) and the semantic scorer
    (cosine similarity over the same vector space) read from this one fit,
    so their scores stay comparable when fused."""
    texts = [f"{chunk.metadata_text} {chunk.text}" for chunk in chunks]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, stop_words="english")
    matrix = vectorizer.fit_transform(texts)
    return vectorizer, matrix
