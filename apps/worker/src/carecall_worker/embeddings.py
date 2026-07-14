import hashlib
from typing import List

EMBEDDING_MODEL_NAME = "mock-hash-embedding-v1"
EMBEDDING_DIM = 1536


def compute_mock_embedding(text: str, dim: int = EMBEDDING_DIM) -> List[float]:
    """Deterministic, offline pseudo-embedding: hash the text and tile the
    resulting bytes (mapped to [-1, 1]) out to `dim`. This is NOT a
    semantic embedding - it exists so the pgvector column, index, and
    worker pipeline can be exercised end-to-end without an OpenAI API key.
    A real OpenAIEmbeddingProvider is a drop-in swap behind the same
    call site (see docs/architecture/retrieval.md)."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values = [(byte / 255.0) * 2 - 1 for byte in digest]
    tiled = (values * (dim // len(values) + 1))[:dim]
    return tiled
