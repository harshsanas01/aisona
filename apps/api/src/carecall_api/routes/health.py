from typing import Dict

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get('/api/health')
def health(request: Request) -> Dict[str, object]:
    container = request.app.state.container
    if container is None:
        raise HTTPException(status_code=500, detail='Transcript corpus is unavailable')
    return {
        'status': 'ok',
        'calls_loaded': len(container.call_repository.list_calls()),
        'retrieval_mode': 'hybrid',
    }
