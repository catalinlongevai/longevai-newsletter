from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import JSONResponse, Response

from app.api.routes import router as api_router
from app.core.auth import enforce_api_auth
from app.core.config import get_settings
from app.core.observability import REQUEST_COUNT, REQUEST_LATENCY
from app.core.responses import error_response
from app.db.init_db import init_db
from app.db.session import get_engine

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument(engine=get_engine())
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(api_router)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-Id", str(uuid4()))
    request.state.trace_id = trace_id

    if request.url.path.startswith("/v1") and request.method in {"POST", "PATCH", "PUT", "DELETE"}:
        try:
            enforce_api_auth(request)
        except HTTPException as exc:
            payload, status = error_response("AUTH_ERROR", str(exc.detail), trace_id, exc.status_code)
            return JSONResponse(payload, status_code=status)

    start = perf_counter()
    response = await call_next(request)
    elapsed = perf_counter() - start

    path = request.url.path
    REQUEST_COUNT.labels(request.method, path, str(response.status_code)).inc()
    REQUEST_LATENCY.labels(request.method, path).observe(elapsed)
    response.headers["X-Trace-Id"] = trace_id
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    payload, status = error_response(
        code="HTTP_ERROR",
        message=str(exc.detail),
        trace_id=getattr(request.state, "trace_id", "missing-trace-id"),
        status=exc.status_code,
    )
    return JSONResponse(payload, status_code=status)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    payload, status = error_response(
        code="INTERNAL_ERROR",
        message=str(exc),
        trace_id=getattr(request.state, "trace_id", "missing-trace-id"),
        status=500,
    )
    return JSONResponse(payload, status_code=status)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    payload, status = error_response(
        code="VALIDATION_ERROR",
        message="Request validation failed",
        trace_id=getattr(request.state, "trace_id", "missing-trace-id"),
        status=422,
        details={"errors": exc.errors()},
    )
    return JSONResponse(payload, status_code=status)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
