FROM python:3.11-slim
WORKDIR /app

COPY packages/domain packages/domain
COPY packages/application packages/application
COPY packages/retrieval packages/retrieval
COPY packages/llm packages/llm
COPY packages/persistence packages/persistence
COPY packages/observability packages/observability
COPY apps/api apps/api
COPY data data

RUN pip install --no-cache-dir \
    ./packages/domain \
    ./packages/application \
    ./packages/retrieval \
    ./packages/llm \
    ./packages/observability \
    "./packages/persistence[postgres]" \
    "./apps/api[postgres]"

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

CMD ["uvicorn", "carecall_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "apps/api/src"]
