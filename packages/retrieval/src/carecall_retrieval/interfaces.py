from typing import Protocol

from carecall_domain import Chunk


class Scorer(Protocol):
    """Structural interface shared by lexical and semantic scorers so
    HybridRetriever can fuse arbitrary scorer implementations - e.g. a real
    embedding-backed SemanticScorer could later replace the current TF-IDF
    proxy without changing the fusion logic."""

    def score(self, query: str, chunk: Chunk) -> float: ...
