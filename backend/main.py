"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from backend.api.v1.router import router as api_v1_router
from backend.exceptions import AppException
from backend.logging_config import bind_trace_id, configure_logging, get_logger
from backend.metrics import API_REQUEST_DURATION_SECONDS, HTTP_REQUESTS_TOTAL
from backend.settings import Settings, get_settings
from backend.telemetry import configure_telemetry

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan — configure logging and telemetry on startup."""
    settings = get_settings()
    configure_logging(debug=settings.app_debug)
    configure_telemetry(settings)
    logger.info("application_started", app_env=settings.app_env, version=settings.app_version)
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    resolved_settings = settings or get_settings()

    app = FastAPI(
        title="TaskFlow AI",
        version=resolved_settings.app_version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        start = perf_counter()
        response = await call_next(request)
        duration = perf_counter() - start
        path = request.url.path
        API_REQUEST_DURATION_SECONDS.labels(request.method, path).observe(duration)
        HTTP_REQUESTS_TOTAL.labels(request.method, path, str(response.status_code)).inc()
        return response

    @app.middleware("http")
    async def trace_id_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        trace_id = request.headers.get("X-Trace-Id", uuid4().hex)
        bind_trace_id(trace_id)
        request.state.trace_id = trace_id
        response = await call_next(request)
        response.headers["X-Trace-Id"] = trace_id
        return response

    @app.exception_handler(AppException)
    async def app_exception_handler(_request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {
            "status": "healthy",
            "version": resolved_settings.app_version,
        }

    app.include_router(api_v1_router, prefix="/api/v1")
    app.mount("/metrics", make_asgi_app())

    return app


app = create_app()
