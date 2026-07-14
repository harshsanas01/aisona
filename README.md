# CareCall Insight

CareCall Insight is an internal QA tool for care coordinators. A coordinator asks a natural-language question about the care-call transcript corpus and gets back a grounded answer with citations (patient, call ID, date, exact turn range, quote) that can be opened as the full source transcript. It also surfaces operational safety-relevant highlights (falls, missed medication, etc.) and supports patient/date filtering.

This repository started as a timed take-home exercise and has since been evolved into a modular-monolith monorepo: layered domain/application/retrieval/LLM/persistence packages, a PostgreSQL+pgvector production-like storage mode alongside the original in-memory demo mode, durable ingestion, streaming answers, a background embedding worker, CI, and Docker Compose - while preserving every behavior that worked in the original submission.

## 1. Quick start

### Demo mode (in-memory, no Docker, no database)

```bash
cp .env.example .env
make setup
make backend     # terminal 1 - FastAPI on :8000
make web          # terminal 2 - Vite dev server on :5173
```

Open http://localhost:5173. Works with no OpenAI key (`CARECALL_ANSWER_MODE=mock` by default) and no PostgreSQL.

### Production-like mode (PostgreSQL + pgvector, one command)

```bash
cp .env.example .env
docker compose up --build
```

This starts Postgres+pgvector, runs Alembic migrations, then the API (bootstrapping the fixture corpus into the database on first boot), a background embedding worker, and the web app behind nginx (proxying `/api` to the API, with buffering disabled so the streaming endpoint works). Web: http://localhost:5173. API: http://localhost:8000.

## 2. Architecture summary

A modular monolith, not microservices - see [ARCHITECTURE.md](ARCHITECTURE.md) for the full writeup and why.

```
apps/api      FastAPI delivery layer (routes, DI wiring, middleware)
apps/web      React + Vite frontend, organized by feature
apps/worker   Background polling worker (embedding backfill)

packages/domain          Entities, value objects, domain services - no framework imports
packages/application      Use cases + ports (interfaces) - depends only on domain
packages/retrieval        Chunking + hybrid lexical/semantic retrieval
packages/llm              Answer generators (mock/OpenAI) + the grounding pipeline
packages/persistence      In-memory and PostgreSQL repository implementations
packages/observability    Structured JSON logging + Prometheus-style metrics
```

Every cross-package dependency implements a port defined in `packages/application/ports` - swapping in-memory for PostgreSQL, or mock for OpenAI, never touches a use case or a route.

## 3. Features

- Natural-language Q&A grounded in the transcript corpus, with server-owned citations (call/patient/date/turn-range/quote) - never generator-supplied.
- Hybrid lexical + semantic retrieval with configurable fusion weights, a minimum relevance threshold, evidence diversification by call, and a pluggable reranker interface.
- A real multi-stage grounding pipeline that rejects out-of-domain questions (weather, sports, crypto, trivia, jokes), medical-advice-seeking questions, and post-generation "does this evidence actually relate to this question" checks - not just a relevance-score cutoff. See [docs/architecture/grounding.md](docs/architecture/grounding.md).
- Patient and date-range filtering, with an active-filter summary and a distinct "no calls match your filters" empty state.
- Deterministic, fully-offline safety-relevant highlighting (dizziness, falls/near-falls, missed medication, medication changes, sleep, meals, glucose, respiratory, transportation, home safety) with a legend and category filter in the transcript view - explicitly labeled as operational triage support, not a medical diagnosis.
- Streaming answers over Server-Sent Events (`POST /api/ask/stream`), with cancellation via `AbortController`; the original synchronous `POST /api/ask` is unchanged.
- Durable transcript ingestion (`POST /api/calls`, `POST /api/calls/batch`, bounded at 20 per batch) - idempotent on external call ID, and a newly ingested call is searchable immediately (no restart).
- Two storage modes, one codebase: in-memory (demo) and PostgreSQL+pgvector (production-like), selected by `CARECALL_STORAGE_MODE`.
- A background worker that backfills pgvector embeddings without ever being required for the API to function.
- Structured JSON logs, `/api/metrics` (Prometheus text), `/api/health` (liveness) and `/api/readiness`.

## 4. Retrieval and grounding

**Retrieval** (`packages/retrieval`): overlapping 2-4 turn dialogue windows per call, scored by an IDF-weighted lexical overlap and a TF-IDF cosine-similarity semantic proxy, fused with configurable weights plus small symptom/name-aware boosts, gated by a minimum relevance threshold, and diversified by call before being capped at top-k. Full algorithm: [docs/architecture/retrieval.md](docs/architecture/retrieval.md).

**Grounding** (`packages/llm/grounding`, orchestrated by `AskQuestionUseCase`): query validation and scope classification run *before* retrieval; evidence sufficiency and post-generation support validation run *after* generation but *before* the answer ever reaches the caller. This is what makes "What is today's weather in LA?" and "Tell me a joke." return no evidence instead of a confident answer built from an unrelated quote - see [docs/architecture/grounding.md](docs/architecture/grounding.md) for the full pipeline and the specific bug this replaced.

## 5. API overview

Legacy endpoints (preserved exactly, still what the frontend uses):

```
GET  /api/health
GET  /api/readiness
GET  /api/metrics
GET  /api/calls
GET  /api/calls/{call_id}
GET  /api/patients
GET  /api/safety-events?call_id=&category=
POST /api/ask
POST /api/ask/stream        (SSE)
POST /api/calls              (ingest one call)
POST /api/calls/batch        (ingest up to 20 calls)
```

`POST /api/ask` request: `{"question": str, "patient_id": str|null, "start_date": "YYYY-MM-DD"|null, "end_date": "YYYY-MM-DD"|null}`. Response includes `citations`, `retrieval_debug`, and the `filters` actually applied. An invalid date range (`start_date` after `end_date`) returns 422.

## 6. Evaluation results

```
make eval
```

- Original 8-question retrieval set: **8/8** hit rate (every expected call cited).
- Retrieval metrics (`scripts/evaluate_retrieval.py`): mean recall 1.00, mean precision 0.62, mean reciprocal rank 0.81, unanswerable accuracy 100%.
- Grounded-answer evaluation (`scripts/evaluate_grounding.py`, deterministic structural/lexical checks - not an LLM judge): **19/19** passed across the original 8 plus 11 adversarial questions (4 out-of-domain, 2 medical-advice, 3 fall-attribution/third-party, 1 chest-pain) - every citation resolves to a real call/turn range with a verbatim quote, no citations on unanswerable responses, and the fall-attribution questions never misattribute Gus's fall to Samuel or Margaret.

## 7. Known limitations

- The "semantic" retrieval signal is a TF-IDF cosine-similarity proxy, not a learned embedding - it won't generalize to true synonyms with zero lexical overlap. Real embeddings (OpenAI or the worker's mock embedding) exist in the pgvector column but aren't yet wired into a query-time semantic search path - see [ARCHITECTURE.md](ARCHITECTURE.md) roadmap.
- The out-of-domain/medical-advice query classifier is a topic-category keyword list, not a learned classifier - broad enough to generalize past the specific adversarial test questions, but not exhaustive.
- The mock answer generator is genuinely extractive (quotes the real top-matched turn) but is not a real language model - OpenAI mode is required for fluent, synthesized answers.
- No authentication/authorization is implemented (not requested; would be required before any real deployment).
- Evaluation is still a curated question set (8 + 11), not a large held-out benchmark.

## 8. Security and privacy notes

The dataset is fictional, but the code is written as if it weren't: no API keys ever reach the browser bundle or logs, structured logs never contain question/answer/transcript text (see [packages/observability](packages/observability)), CORS should be restricted to known origins in any real deployment (currently permissive for local dev), and batch ingestion is bounded. **This is not a HIPAA-compliant system and makes no such claim** - a real deployment over real PHI would need, at minimum, authentication/authorization, encryption at rest, an audit trail beyond `question_audit`, and a signed BAA with every subprocessor.

## 9. Roadmap

1. Wire a real embedding-backed semantic search path (query-time OpenAI or local embeddings) behind the existing `SemanticScorer` interface - the pgvector column and worker backfill already exist.
2. Learned/LLM-assisted query intent classification behind the existing `AnswerabilityGate.is_query_out_of_scope` extension point, replacing the keyword deny-list.
3. Authentication/authorization and per-coordinator access scoping.

## 10. AI-tool disclosure

AI coding tools (Claude Code) were used extensively to accelerate this refactor - scaffolding the layered packages, writing tests, and reviewing/debugging the grounding pipeline. Every change was verified by running the actual test suite, evaluation scripts, and a live browser session (via Playwright) against the real running application, not just written and assumed correct.
