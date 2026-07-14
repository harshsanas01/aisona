import logging
import time
import uuid
from contextvars import ContextVar

from carecall_observability import increment, log_event, observe
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("carecall_api.request")

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns a request id (echoed as X-Request-ID), times the request,
    records HTTP-level metrics, and logs one structured JSON line per
    request - method/path/status/latency only, never request or response
    bodies (no questions, answers, or transcript content at this layer)."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        token = request_id_var.set(request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            increment("carecall_http_requests_total", endpoint=request.url.path, status="500")
            raise
        finally:
            request_id_var.reset(token)

        latency_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        increment("carecall_http_requests_total", endpoint=request.url.path, status=str(response.status_code))
        observe("carecall_http_request_latency_ms", latency_ms, endpoint=request.url.path)
        log_event(
            logger, "http_request",
            request_id=request_id, method=request.method, path=request.url.path,
            status=response.status_code, latency_ms=round(latency_ms, 2),
        )
        return response
