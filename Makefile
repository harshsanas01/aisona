.PHONY: setup backend frontend dev test eval

setup:
	python3 -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip
	. .venv/bin/activate && pip install \
		-e packages/domain \
		-e packages/application \
		-e packages/retrieval \
		-e packages/llm \
		-e packages/persistence \
		-e "apps/api[dev]"
	npm install --prefix frontend

backend:
	. .venv/bin/activate && uvicorn carecall_api.main:app --reload --port 8000 --app-dir apps/api/src

frontend:
	npm --prefix frontend run dev

dev:
	@echo "Run 'make backend' and 'make frontend' in separate terminals"

test:
	. .venv/bin/activate && python -m pytest apps/api/tests -v

eval:
	. .venv/bin/activate && python scripts/evaluate.py
