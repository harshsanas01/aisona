from carecall_domain import TranscriptDataError
from carecall_observability import configure_logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from . import config
from .lifespan import build_container, lifespan
from .middleware import RequestContextMiddleware
from .routes import (
    audit,
    briefs,
    calls,
    feedback,
    health,
    ingestion,
    metrics,
    patient_patterns,
    patient_timeline,
    patients,
    person_mentions,
    questions,
    retrieval_lab,
    safety,
    tasks,
)

configure_logging(config.LOG_LEVEL)

app = FastAPI(title='CareCall Insight', version='0.1.0', lifespan=lifespan)
app.add_middleware(RequestContextMiddleware)

# Also build eagerly at import time: FastAPI's TestClient only triggers the
# lifespan context manager when used as `with TestClient(app) as client`,
# and the existing test suite instantiates TestClient directly without a
# context manager. This keeps app.state.container populated either way.
try:
    app.state.container = build_container()
except TranscriptDataError:
    app.state.container = None


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={'detail': exc.errors()})


app.include_router(health.router)
app.include_router(calls.router)
app.include_router(questions.router)
app.include_router(ingestion.router)
app.include_router(patients.router)
app.include_router(patient_timeline.router)
app.include_router(patient_patterns.router)
app.include_router(person_mentions.router)
app.include_router(tasks.router)
app.include_router(briefs.router)
app.include_router(audit.router)
app.include_router(feedback.router)
app.include_router(retrieval_lab.router)
app.include_router(safety.router)
app.include_router(metrics.router)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('carecall_api.main:app', host='0.0.0.0', port=config.BACKEND_PORT, reload=False)
