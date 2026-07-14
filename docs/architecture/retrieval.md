# Retrieval: the exact ranking algorithm

Implemented in `packages/retrieval/src/carecall_retrieval/hybrid.py`. See [ADR 0002](../adr/0002-hybrid-retrieval.md) for why hybrid at all.

## 1. Chunking

`packages/retrieval/src/carecall_retrieval/chunking.py` builds overlapping 2-4 turn dialogue windows per call (every starting position, window size capped at 4, minimum 2). Each chunk keeps:

- the original turn objects (so citations can be built with exact turn numbers and exact text)
- `metadata_text`: patient name, patient id, date, call id, and the window's raw turn text (used only for lexical/semantic scoring, never surfaced directly)
- `text`: the window rendered as `"speaker: text"` lines joined by spaces (what a citation quote is derived from)

## 2. Vector space

`vectorization.py` fits **one** `TfidfVectorizer` (1-2 grams, English stopwords) over every chunk's `metadata_text + text`. Both scorers below read from this single fit, so their scores are comparable when fused.

## 3. Lexical score

`lexical.py`: for each query term that survives filtering (length >= 3, not a stopword, and - critically - not appearing in more than 12% of chunks, which filters out corpus-wide filler like "today" or "amy" without needing a hand-maintained list), the term's IDF weight from the shared vectorizer is looked up. The lexical score is `matched_weight / total_weight` - rare, discriminating terms dominate the score; a term absent from the corpus entirely is treated as maximally rare.

**Known limitation deliberately left in**: this filter is *relative* (a document-frequency ratio), not absolute. A generic verb that happens to sit just under the 12% cutoff (e.g. "tell", present in ~6.6% of chunks) can still contribute real IDF-weighted score to an unrelated query like "Tell me a joke." This is exactly the failure this system found and fixed - not by tightening the lexical filter further (which just moves the goalposts), but by adding `QueryIntentClassifier` as an independent pre-retrieval gate and `DeterministicSupportValidator` as an independent post-generation gate. See [grounding.md](grounding.md).

## 4. Semantic score

`semantic.py`: cosine similarity between the query vector and a chunk's vector in the *same* TF-IDF space. This is a **proxy**, not a learned embedding - it captures shared n-gram overlap (including some paraphrase via shared bigrams) but will not generalize to true synonyms with zero lexical overlap ("trouble sleeping" vs "insomnia", for example, would not connect). The pgvector column and the `EmbeddingProvider`-shaped worker backfill (`apps/worker`) exist specifically so a real embedding-backed `SemanticScorer` can be swapped in later without touching `HybridRetriever`'s fusion logic.

## 5. Fusion and boosts

```
score = CARECALL_LEXICAL_WEIGHT * lexical + CARECALL_SEMANTIC_WEIGHT * semantic + boost
```

Defaults: lexical 0.45, semantic 0.55 (both env-configurable). `boost` is the sum of:

- **+0.2** if the chunk's own `patient_name` appears in the query.
- **+0.15** per capitalized query word (excluding sentence-starter words like "Did"/"What" and calendar words like month/day names) that appears verbatim in the chunk's text - this is what lets a third-party name mentioned only inside another patient's call (e.g. "Gus", mentioned in Samuel Rivera's call_021) get boosted, which the patient-name boost alone can't do.
- **up to +1.1** of curated medication-specific boosts (lisinopril / "started me on a new blood pressure pill" / "first mentioned") - narrow and specific enough that they can't fire on an unrelated query.
- **+0.03** each if the chunk's date falls inside an applied `start_date`/`end_date` filter.
- **+0.08** per symptom-family keyword (dizzy, sleep/waking/rest, cough, fall/fell/tripped/sprained, medication/pill/lisinopril) that both the query and chunk mention - these only ever fire when the query itself names the symptom family, so an out-of-domain query gets zero benefit from them.

## 6. Gating, reranking, diversification

- Anything scoring below `CARECALL_MIN_RELEVANCE_SCORE` (default 0.15) is dropped before ranking - this, not a hardcoded keyword list, is what makes "What is the capital of France?" return zero chunks.
- `Reranker` (default `IdentityReranker`, a real no-op) is applied next - a cross-encoder or LLM-based reranker is a drop-in replacement.
- Finally, results are diversified by call (one call can't crowd out every slot) and capped at `CARECALL_TOP_K` (default 8).

## 7. Refreshing after ingestion

`HybridRetriever.refresh(chunks)` rebuilds the vectorizer, matrix, and both scorers from a new chunk list. `IngestCallUseCase` calls this after every successful ingestion, which is what makes a newly ingested call searchable immediately instead of only after a process restart.
