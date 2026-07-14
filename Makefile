.PHONY: help setup dev backend web test test-unit test-integration test-e2e eval prompt-eval lint format typecheck migrate seed smoke test-contract clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

setup: ## Install all Python packages (editable) and frontend dependencies
	python3 -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip
	. .venv/bin/activate && pip install \
		-e packages/domain \
		-e packages/application \
		-e packages/retrieval \
		-e packages/llm \
		-e packages/persistence \
		-e packages/observability \
		-e "apps/api[dev]" \
		-e "apps/worker[dev]" \
		ruff mypy
	npm install --prefix apps/web

dev: ## One-command local stack: postgres + migrate + api + worker + web (Docker)
	docker compose up --build

backend: ## Run the API locally against demo (in-memory) mode
	. .venv/bin/activate && uvicorn carecall_api.main:app --reload --port 8000 --app-dir apps/api/src

web: ## Run the Vite dev server locally
	npm --prefix apps/web run dev

test: ## Run the full Python test suite (memory mode; Postgres cases auto-skip)
	. .venv/bin/activate && python -m pytest apps/api/tests apps/worker/tests tests/contract -v

test-unit: ## Fast tests only: no Docker/Postgres required
	. .venv/bin/activate && python -m pytest apps/api/tests apps/worker/tests -v

test-integration: ## Contract + worker tests against a real, disposable Postgres
	docker compose up -d postgres
	docker compose run --rm migrate
	. .venv/bin/activate && DATABASE_URL=postgresql+psycopg://carecall:carecall@localhost:5442/carecall \
		python -m pytest tests/contract apps/worker/tests -v
	docker compose down

test-contract: ## Just the repository contract tests (in-memory only unless DATABASE_URL is set)
	. .venv/bin/activate && python -m pytest tests/contract -v

test-e2e: smoke ## End-to-end checklist against a running API (alias for smoke)

eval: ## Run all three evaluation layers (hit-rate, retrieval metrics, grounded-answer checks)
	. .venv/bin/activate && python scripts/evaluate.py
	. .venv/bin/activate && python scripts/evaluate_retrieval.py
	. .venv/bin/activate && python scripts/evaluate_grounding.py

prompt-eval: ## Prompt/model/retrieval-config regression gate against data/evaluation/prompt_eval_baseline.json
	. .venv/bin/activate && python scripts/prompt_eval.py

lint: ## Ruff lint check across all Python packages
	. .venv/bin/activate && ruff check packages apps/api/src apps/worker/src scripts

format: ## Ruff autoformat across all Python packages
	. .venv/bin/activate && ruff format packages apps/api/src apps/worker/src scripts tests

typecheck: ## mypy (Python) + tsc (frontend)
	. .venv/bin/activate && mypy packages/domain/src packages/application/src packages/retrieval/src packages/llm/src packages/persistence/src packages/observability/src apps/api/src apps/worker/src --ignore-missing-imports
	npm --prefix apps/web run typecheck

migrate: ## Apply Alembic migrations to DATABASE_URL (defaults to localhost:5432)
	. .venv/bin/activate && cd packages/persistence && alembic upgrade head

seed: ## Seed a running API's storage with the fixture transcripts via POST /api/calls/batch
	. .venv/bin/activate && python scripts/ingest_fixture_data.py

smoke: ## End-to-end HTTP checklist against a running API (default http://localhost:8000)
	. .venv/bin/activate && bash scripts/smoke_test.sh

clean: ## Remove caches and build artifacts (keeps .venv and node_modules)
	find . -name "__pycache__" -not -path "./.venv/*" -not -path "*/node_modules/*" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.egg-info" -not -path "./.venv/*" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache apps/web/dist artifacts
