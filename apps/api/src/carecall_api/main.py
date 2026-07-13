from contextlib import asynccontextmanager
from typing import Dict

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .answer_service import AnswerService
from .config import BACKEND_PORT, TRANSCRIPTS_PATH
from .data_loader import TranscriptDataError, load_transcripts
from .models import AskRequest, AskResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.corpus = load_transcripts(TRANSCRIPTS_PATH)
        app.state.answer_service = AnswerService(app.state.corpus)
    except TranscriptDataError as exc:
        raise RuntimeError(str(exc)) from exc
    yield


app = FastAPI(title='CareCall Insight', version='0.1.0', lifespan=lifespan)


try:
    app.state.corpus = load_transcripts(TRANSCRIPTS_PATH)
    app.state.answer_service = AnswerService(app.state.corpus)
except TranscriptDataError as exc:
    app.state.corpus = None
    app.state.answer_service = None


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={'detail': exc.errors()})


@app.get('/api/health')
def health() -> Dict[str, object]:
    if app.state.corpus is None:
        raise HTTPException(status_code=500, detail='Transcript corpus is unavailable')
    return {
        'status': 'ok',
        'calls_loaded': len(app.state.corpus.calls),
        'retrieval_mode': 'hybrid',
    }


@app.get('/api/calls')
def list_calls() -> Dict[str, object]:
    if app.state.corpus is None:
        raise HTTPException(status_code=500, detail='Transcript corpus is unavailable')
    return {'calls': [
        {
            'call_id': call.call_id,
            'date': call.date,
            'patient_name': call.patient.name,
        }
        for call in app.state.corpus.calls
    ]}


@app.get('/api/calls/{call_id}')
def get_call(call_id: str) -> Dict[str, object]:
    if app.state.corpus is None:
        raise HTTPException(status_code=500, detail='Transcript corpus is unavailable')
    call = next((item for item in app.state.corpus.calls if item.call_id == call_id), None)
    if call is None:
        raise HTTPException(status_code=404, detail='Call not found')
    return {
        'call_id': call.call_id,
        'date': call.date,
        'patient': {'id': call.patient.id, 'name': call.patient.name, 'age': call.patient.age},
        'duration_seconds': call.duration_seconds,
        'turns': [
            {'turn_number': idx + 1, 'speaker': turn.speaker, 'text': turn.text}
            for idx, turn in enumerate(call.turns)
        ],
    }


@app.post('/api/ask', response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    if app.state.answer_service is None:
        raise HTTPException(status_code=500, detail='Transcript corpus is unavailable')
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=422, detail='Question must not be empty')
    return app.state.answer_service.answer(
        request.question,
        patient_id=request.patient_id,
        start_date=request.start_date,
        end_date=request.end_date,
    )


if __name__ == '__main__':
    uvicorn.run('carecall_api.main:app', host='0.0.0.0', port=BACKEND_PORT, reload=False)
