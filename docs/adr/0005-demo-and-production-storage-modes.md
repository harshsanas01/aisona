# ADR 0005: Both a demo (in-memory) and a production-like (PostgreSQL) storage mode

## Status
Accepted

## Context
This started as a timed take-home exercise where fast startup and zero external dependencies were the whole point of the in-memory design - and that's still a legitimate need (a candidate/demo environment, or any contributor's laptop with no Docker running). At the same time, "production-capable persistence" was an explicit requirement for the evolved version. Neither need should force out the other: requiring Postgres for local development would slow down the inner loop for everyone; keeping only in-memory storage would mean the system never actually gets exercised the way it would run in production.

## Decision
Both modes implement the exact same repository ports (`CallRepository`, `PatientRepository`, `ChunkRepository`), selected at startup by `CARECALL_STORAGE_MODE=memory|postgres` in `apps/api/lifespan.py`. Repository contract tests (`tests/contract/`) run the identical assertion suite against both implementations - the in-memory case always, the PostgreSQL case only when `DATABASE_URL` is set. No unit test, and no basic local dev workflow, requires PostgreSQL to exist.

## Consequences
- A new contributor can `make setup && make backend && make web` and be productive with zero Docker/Postgres knowledge.
- `docker compose up --build` gives the full production-like path (Postgres + pgvector + migrations + worker) as a single command when that's what's being verified.
- Any behavioral divergence between the two modes is a contract test failure, not a production surprise - this already caught one real bug during development (`InMemoryPatientRepository` needed to read live from `CallRepository`, matching Postgres's always-current behavior, instead of a stale snapshot dict built once at startup).
- Cost accepted: two repository implementations to maintain per port, kept small and mechanical (no business logic lives in either - see `packages/persistence`).
