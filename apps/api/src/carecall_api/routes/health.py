from typing import Dict

from fastapi import APIRouter, HTTPException, Request

from .. import config

router = APIRouter()


@router.get('/api/health')
def health(request: Request) -> Dict[str, object]:
    """Liveness: is the process up and did startup succeed at all."""
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail='Transcript corpus is unavailable')
    return {
        'status': 'ok',
        'calls_loaded': len(container.call_repository.list_calls()),
        'retrieval_mode': 'hybrid',
        # Additive fields consumed by the web app's header status badges.
        'storage_mode': config.STORAGE_MODE,
        'answer_mode': config.ANSWER_MODE,
        # Lets the frontend hide developer-only surfaces (Why this answer?,
        # Retrieval Lab) instead of showing them and then 403ing.
        'developer_mode': config.DEVELOPER_MODE,
    }


@router.get('/api/readiness')
def readiness(request: Request) -> Dict[str, object]:
    """Readiness: is the container wired AND can it actually serve a
    request right now - e.g. re-runs a trivial repository call so a lost
    PostgreSQL connection in production-like mode fails readiness before it
    fails a real user request."""
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=503, detail='Not ready: container failed to initialize')
    try:
        container.call_repository.list_calls()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f'Not ready: {exc}') from exc
    return {'status': 'ready'}
