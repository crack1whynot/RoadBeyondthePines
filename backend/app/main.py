"""FastAPI application and explicit application lifecycle."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.routes.agents import router as agents_router
from backend.api.routes.brain import router as brain_router
from backend.api.routes.health import router as health_router
from backend.api.routes.management import router as management_router
from backend.api.routes.memory import router as memory_router
from backend.api.routes.orchestrator import router as orchestrator_router
from backend.api.routes.providers import router as providers_router
from backend.api.routes.settings import router as settings_router
from backend.api.routes.tasks import router as tasks_router
from backend.api.routes.unreal_mcp import router as unreal_mcp_router
from backend.core.config import settings
from backend.core.di import AppContainer, create_app_container
from backend.core.logging import configure_logging, get_logger

logger = configure_logging()


def _attach_container(application: FastAPI, container: AppContainer) -> None:
    """Expose the sole composition root to HTTP delivery adapters."""

    application.container = container
    application.state.container = container
    application.state.runtime = container.runtime
    application.state.orchestrator = container.orchestrator
    application.state.unreal_mcp_manager = container.unreal_mcp_manager


@asynccontextmanager
async def application_lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Start and stop application services without import-time side effects."""

    state = application.state
    container = getattr(state, "container", None)
    runtime = getattr(state, "runtime", None)
    manager = getattr(state, "unreal_mcp_manager", None)

    # A real FastAPI app has no container until lifespan startup.  The second
    # branch preserves direct lifecycle tests that supply lightweight fakes.
    if container is None and runtime is None and manager is None:
        container = create_app_container()
        _attach_container(application, container)
        runtime = container.runtime
        manager = container.unreal_mcp_manager

    try:
        if runtime is not None and hasattr(runtime, "start"):
            runtime.start()
        if manager is not None:
            await manager.start()
        yield
    finally:
        if manager is not None:
            await manager.stop()
        if runtime is not None and hasattr(runtime, "shutdown"):
            # Keep the established compatibility call and lifecycle order.
            runtime.shutdown()


def create_app() -> FastAPI:
    """Build the ASGI application without constructing or starting Runtime."""

    application = FastAPI(
        title=settings.app_name,
        version="0.6.0",
        lifespan=application_lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url, "http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health_router)
    application.include_router(agents_router)
    application.include_router(tasks_router)
    application.include_router(settings_router)
    application.include_router(management_router)
    application.include_router(orchestrator_router)
    application.include_router(brain_router)
    application.include_router(memory_router)
    application.include_router(providers_router)
    application.include_router(unreal_mcp_router)

    @application.get("/")
    def read_root() -> dict[str, str]:
        """Root endpoint for health and service discovery."""

        return {"service": settings.app_name, "status": "initialized"}

    return application


app = create_app()


def _safe_validation_errors(exc: RequestValidationError) -> list[dict[str, object]]:
    """Keep validation feedback useful without returning rejected input values."""

    safe_errors: list[dict[str, object]] = []
    for error in exc.errors():
        location = error.get("loc", ())
        if isinstance(location, (list, tuple)):
            safe_location = [
                item if isinstance(item, (str, int)) else type(item).__name__
                for item in location
            ]
        else:
            safe_location = ["unknown"]
        safe_errors.append(
            {
                "loc": safe_location,
                "type": str(error.get("type", "validation_error")),
            }
        )
    return safe_errors


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = _safe_validation_errors(exc)
    logger.warning("Validation failed: %s", errors)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": "Validation failed", "errors": errors},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled error: %s", type(exc).__name__)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )
