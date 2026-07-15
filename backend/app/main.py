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
from backend.core.config import settings
from backend.core.di import create_app_container
from backend.core.logging import configure_logging, get_logger

logger = configure_logging()

app = FastAPI(title=settings.app_name, version="0.1.0")
container = create_app_container()

app.container = container
app.state.container = container
app.state.runtime = container.runtime
app.state.orchestrator = container.orchestrator
if container.runtime is not None:
    container.runtime.register_service("orchestrator", container.orchestrator)
    if container.provider_manager is not None:
        container.runtime.register_service("ai_provider_manager", container.provider_manager)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(agents_router)
app.include_router(tasks_router)
app.include_router(settings_router)
app.include_router(management_router)
app.include_router(orchestrator_router)
app.include_router(brain_router)
app.include_router(memory_router, prefix="")
app.include_router(providers_router)


@app.get("/")
def read_root() -> dict[str, str]:
    """Root endpoint for health and service discovery."""
    return {"service": settings.app_name, "status": "initialized"}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning("Validation failed: %s", exc)
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": "Validation failed", "errors": exc.errors()})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": "Internal server error"})


@app.on_event("shutdown")
def shutdown_runtime() -> None:
    """Shut down the runtime layer during application teardown."""
    runtime = getattr(app.state, "runtime", None)
    if runtime is not None:
        runtime.shutdown()
