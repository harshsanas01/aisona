setup:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -r backend/requirements.txt
	npm install --prefix frontend

backend:
	. .venv/bin/activate && uvicorn backend.app.main:app --reload --port 8000

frontend:
	npm --prefix frontend run dev

dev:
	@echo "Run 'make backend' and 'make frontend' in separate terminals"
