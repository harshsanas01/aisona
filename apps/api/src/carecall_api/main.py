from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from carecall_domain import TranscriptDataError

from . import config
from .lifespan import build_container, lifespan
from .routes import calls, health, questions

app = FastAPI(title='CareCall Insight', version='0.1.0', lifespan=lifespan)

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


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('carecall_api.main:app', host='0.0.0.0', port=config.BACKEND_PORT, reload=False)
