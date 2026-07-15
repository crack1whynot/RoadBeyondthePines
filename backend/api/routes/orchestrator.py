from fastapi import APIRouter, Request

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])


@router.post("/request")
def handle_orchestrator_request(request: Request, request_text: str) -> dict[str, object]:
    """Route a user request through the orchestrator layer."""
    runtime = getattr(request.app.state, "runtime", None)
    if runtime is None:
        raise RuntimeError("Runtime is not initialized")
    orchestrator = runtime.get_service("orchestrator") if hasattr(runtime, "get_service") else None
    if orchestrator is None:
        raise RuntimeError("Orchestrator is not registered")
    return orchestrator.handle_request(request_text)
