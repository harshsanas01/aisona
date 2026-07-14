# ADR 0002: Hybrid lexical + semantic retrieval

## Status
Accepted

## Context
Care-call questions come in two flavors that need different signals: exact-name/exact-term lookups ("What did Frank Delgado say about the van service?" - lexical matching is strong here) and paraphrase-tolerant lookups ("Who has been having trouble sleeping?" matching "I'm up before dawn" - needs something more than exact token overlap).

## Decision
Fuse two scorers over one shared TF-IDF vector space (`packages/retrieval`): an IDF-weighted lexical overlap score, and a cosine-similarity "semantic" score computed in the *same* vector space (a TF-IDF proxy for semantic similarity, not a learned embedding). Fusion is a configurable weighted sum (`CARECALL_LEXICAL_WEIGHT` / `CARECALL_SEMANTIC_WEIGHT`, default 0.45/0.55), plus small, narrowly-scoped boosts (patient/third-party name matches, symptom-family keyword co-occurrence, date-range membership). A minimum relevance threshold and per-call diversification run after fusion. See `docs/architecture/retrieval.md` for the exact formula.

## Consequences
- No embedding API call (or cost, or latency, or API key requirement) is needed for retrieval to work in demo mode - satisfies the "no OpenAI key required" constraint at the retrieval layer, not just the answer-generation layer.
- The TF-IDF "semantic" proxy will not generalize to true synonyms with zero lexical overlap - a known, documented limitation, not an oversight (see `docs/architecture/retrieval.md` §4 and the roadmap in `README.md`).
- A purely statistical score can still be nudged by a generic word (documented concretely in `docs/architecture/grounding.md`'s "Tell me a joke." case) - this is why grounding safety is a separate, independent pipeline (ADR-adjacent: see `docs/architecture/grounding.md`) rather than something retrieval scoring alone is expected to guarantee.
- The pgvector column and the worker's embedding backfill exist specifically so a real embedding-backed semantic scorer is a drop-in replacement behind the same `Scorer`-shaped interface, without changing `HybridRetriever`'s fusion/diversification logic.
