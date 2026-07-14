# ADR 0001: Modular monolith, not microservices

## Status
Accepted

## Context
The candidate brief asked for a small QA tool. The follow-up direction asked for it to evolve into "a scalable and developer-friendly architecture" without becoming distributed-systems complexity for its own sake. The corpus is 21 calls today and will grow, but there's no product requirement today for independently scaling ingestion vs. question-answering, no team boundary that needs a separate deployable per component, and no data-sovereignty reason to split storage.

## Decision
Structure the codebase as a modular monolith inside a monorepo: `packages/domain`, `packages/application`, `packages/retrieval`, `packages/llm`, `packages/persistence`, `packages/observability` are independently installable Python packages with enforced dependency direction (domain has zero framework imports; application depends only on domain; everything else implements application's ports). `apps/api`, `apps/web`, `apps/worker` are the only deployables, all sharing those packages.

## Consequences
- One deployment, one on-call surface, one place to reason about a request end-to-end - a new developer can read `AskQuestionUseCase` top to bottom and see the entire grounded-QA flow.
- No network hop, no serialization, no partial-failure/retry complexity between "retrieval" and "generation" - they're function calls in the same process.
- The boundaries are drawn at exactly the seams a future service split would use (see `ARCHITECTURE.md` §8, scaling strategy), so extracting `packages/retrieval` into its own service later is additive, not a rewrite.
- Trade-off accepted: `apps/api` and `apps/worker` can't be scaled independently from each other today beyond running more replicas of each - acceptable at this corpus size and traffic pattern.
