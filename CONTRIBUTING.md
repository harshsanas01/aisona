# Contributing to CareCall Insight

## Prerequisites

- Python 3.11+
- Node.js 20+ and npm
- Docker (only needed for `docker compose up`, `make test-integration`, or PostgreSQL mode)

## Repository map

```
apps/api        FastAPI delivery layer - routes, DI wiring (lifespan.py), middleware
apps/web        React + Vite frontend, organized by feature under src/features/
apps/worker     Background embedding-backfill worker

packages/domain          Entities, value objects, domain services. No framework imports - ever.
packages/application     Use cases + ports (interfaces). Depends only on carecall_domain.
packages/retrieval       Chunking + hybrid lexical/semantic retrieval. Implements RetrievalService.
packages/llm             Answer generators (mock/OpenAI) + the grounding pipeline stages.
packages/persistence     In-memory and PostgreSQL repository implementations.
packages/observability   Structured JSON logging + Prometheus-style metrics.

data/evaluation   The two question sets that define "correct" for this system.
tests/contract    Same test suite run against every repository implementation.
scripts/          evaluate*.py, ingest_fixture_data.py, smoke_test.py
docs/             Architecture deep-dives and ADRs.
```

See `ARCHITECTURE.md` for the full picture and `docs/architecture/` for retrieval/grounding deep-dives.

## Setup

```bash
cp .env.example .env
make setup
```

## Running things

```bash
make backend          # API on :8000, in-memory mode
make web               # Vite dev server on :5173
docker compose up --build   # full stack: postgres, migrate, api, worker, web
```

## Tests

```bash
make test              # everything, in-memory mode (Postgres cases auto-skip without DATABASE_URL)
make test-unit          # apps/api/tests + apps/worker/tests only
make test-integration    # contract + worker tests against a real, disposable Postgres (needs Docker)
make eval               # all three evaluation layers
make smoke               # end-to-end HTTP checklist against a running API
```

## Coding standards

- `make lint` (ruff) and `make typecheck` (mypy + tsc) must pass before a PR.
- Domain layer (`packages/domain`) must never import FastAPI, SQLAlchemy, OpenAI, or anything HTTP-related. If you find yourself wanting to, the logic belongs in `packages/application`, `packages/llm`, or `packages/persistence` instead.
- Prefer a real, swappable implementation over an abstract interface with only one implementation - every port in `packages/application/ports` exists because there are (or clearly will be) at least two implementations.
- No comments explaining *what* code does - name things so it's obvious. Comments are for *why* (a non-obvious constraint, a workaround, a calibration decision) - see `packages/retrieval/src/carecall_retrieval/hybrid.py` for examples.

## How to add a new endpoint

1. Add or extend a use case in `packages/application/src/carecall_application/use_cases/` if new orchestration logic is needed.
2. Add the route in `apps/api/src/carecall_api/routes/<name>.py`, using `request.app.state.container.<use_case>`.
3. Register the router in `apps/api/src/carecall_api/main.py`.
4. Add pydantic request/response schemas either inline in the route file (if only used there) or in `schemas.py`.
5. Add tests in `apps/api/tests/`.

## How to add a new repository implementation

1. Implement the relevant port from `packages/application/src/carecall_application/ports/repositories.py` in a new module under `packages/persistence/src/carecall_persistence/`.
2. Add it to `tests/contract/` so it's held to the same behavior as the existing implementations.
3. Wire it into `apps/api/src/carecall_api/lifespan.py` behind a new `CARECALL_STORAGE_MODE` value (or extend an existing branch).

## How to add an LLM provider

1. Implement `AnswerGenerator` (`packages/application/src/carecall_application/ports/answer_generator.py`) in `packages/llm/src/carecall_llm/providers/`.
2. It must never return a call id, patient id, turn number, quote, or date directly - only `used_evidence_ids` referencing chunk ids it was given (see ADR 0003).
3. Wire it into `apps/api/src/carecall_api/lifespan.py`'s `build_container()`, selected by a new `CARECALL_ANSWER_MODE` value.

## How to add an evaluation case

- Original retrieval-hit-rate question: add to `data/evaluation/carecall_questions.json` (`id`, `question`, `expected_source_calls`).
- Adversarial/grounding question: add to `data/evaluation/adversarial_questions.json` (`expected_answerable`, and optionally `expected_source_calls` or `forbidden_source_calls` for attribution checks). Run `python scripts/evaluate_grounding.py` to verify.

## Commit conventions

Conventional-commit-style prefixes: `feat:`, `fix:`, `refactor:`, `chore:`, `ci:`, `docs:`, `test:`. Each commit should be independently meaningful and leave the test suite green - see the git log on `feat/production-architecture` for the pattern this repo was actually built with (one phase per commit, each verified before moving on).

## Architecture rules (enforced by convention, not yet by a linter)

- `packages/domain` imports nothing outside the standard library.
- `packages/application` imports only `carecall_domain`.
- Everything else (`packages/retrieval`, `packages/llm`, `packages/persistence`) implements application's ports; application never imports a concrete implementation.
- `apps/api` is the only place concrete implementations get wired together (in `lifespan.py`).
