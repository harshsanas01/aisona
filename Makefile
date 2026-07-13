.PHONY: setup backend web dev test eval

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
	npm install --prefix apps/web

backend:
	. .venv/bin/activate && uvicorn carecall_api.main:app --reload --port 8000 --app-dir apps/api/src

web:
	npm --prefix apps/web run dev

dev:
	@echo "Run 'make backend' and 'make web' in separate terminals"

test:
	. .venv/bin/activate && python -m pytest apps/api/tests -v

eval:
	. .venv/bin/activate && python scripts/evaluate.py
