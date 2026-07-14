FROM python:3.11-slim
WORKDIR /app

COPY packages/domain packages/domain
COPY packages/application packages/application
COPY packages/persistence packages/persistence
COPY apps/worker apps/worker

RUN pip install --no-cache-dir \
    ./packages/domain \
    ./packages/application \
    "./packages/persistence[postgres]" \
    ./apps/worker

CMD ["python", "-m", "carecall_worker.main"]
