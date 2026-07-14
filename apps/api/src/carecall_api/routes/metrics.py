from carecall_observability import render_prometheus
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter()


@router.get('/api/metrics', response_class=PlainTextResponse)
def metrics() -> str:
    return render_prometheus()
