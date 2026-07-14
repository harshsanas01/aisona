# ADR 0004: PostgreSQL + pgvector for the production-like path

## Status
Accepted

## Context
The production-like storage mode needs: durable relational data (patients, calls, turns - clear foreign-key relationships, transactional ingestion), and a place to eventually store vector embeddings for real semantic search, without operating two separate database systems.

## Decision
PostgreSQL (via SQLAlchemy 2.x + Alembic) for all relational data, with the `pgvector` extension providing a `Vector` column type on `transcript_chunks.embedding` for the same table - one database, one connection pool, one backup story. `packages/persistence/postgres` implements the same repository ports as the in-memory demo-mode implementation.

## Consequences
- No separate vector database (Pinecone, Weaviate, etc.) to operate, back up, or keep in sync with the relational data - a chunk and its embedding are the same row.
- `pgvector` scales into the hundreds of thousands of vectors with an `ivfflat`/`hnsw` index - well past where this corpus is realistically headed - without a migration to a different system (the index itself isn't added yet; query-time vector search isn't wired in yet either - see `README.md` roadmap and `ARCHITECTURE.md` §8).
- Alembic migrations are the single source of truth for schema evolution in both local dev (`make migrate`) and CI (`api-ci.yml` runs a downgrade/upgrade round-trip as an integrity check).
- Cost accepted: this is a real dependency to run locally (`docker compose up` or a local Postgres install) - mitigated by never making it *required*: in-memory mode is the default, and every unit test runs against it with zero Postgres dependency.
