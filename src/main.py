"""Application entry point."""

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.routes import admin, ai, checkout, subscriptions, usage, webhooks
from src.config import get_settings
from src.exceptions import AppError
from src.logging_config import configure_logging, get_logger
from src.metrics import (
    REQUEST_COUNT,
    REQUEST_LATENCY,
    get_metrics_response,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    settings = get_settings()
    configure_logging(debug=settings.debug)
    log = get_logger("app")
    log.info("starting", app=settings.app_name)

    # Start retry worker background task (disabled when TESTING)
    retry_task = None
    if settings.webhook_retry_worker_enabled and os.getenv("TESTING", "").lower() not in ("1", "true", "yes"):
        from src.jobs.retry_worker import run_retry_worker

        retry_task = asyncio.create_task(
            run_retry_worker(interval_seconds=settings.webhook_retry_worker_interval_seconds)
        )
        log.info("retry_worker_started", interval=settings.webhook_retry_worker_interval_seconds)

    yield

    # Shutdown
    if retry_task:
        retry_task.cancel()
        try:
            await retry_task
        except asyncio.CancelledError:
            pass
        log.info("retry_worker_stopped")


class MetricsMiddleware(BaseHTTPMiddleware):
    """Record request metrics."""

    async def dispatch(self, request: Request, call_next):
        path = request.scope.get("path", "")
        method = request.method
        with REQUEST_LATENCY.labels(method=method, path=path).time():
            response = await call_next(request)
        status = response.status_code
        REQUEST_COUNT.labels(method=method, path=path, status=status).inc()
        return response


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(MetricsMiddleware)

    # Exception handlers
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.message,
                "code": exc.code,
                "details": exc.details,
            },
        )

    # Routes - all under /v1 for consistent API versioning
    app.include_router(webhooks.router, prefix="/v1")
    app.include_router(subscriptions.router, prefix="/v1")
    app.include_router(checkout.router, prefix="/v1")
    app.include_router(admin.router, prefix="/v1")
    app.include_router(usage.router, prefix="/v1")
    app.include_router(ai.router, prefix="/v1")

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/metrics")
    async def metrics():
        return get_metrics_response()

    return app


app = create_app()
