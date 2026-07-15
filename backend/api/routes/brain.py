from fastapi import APIRouter, Request

router = APIRouter(prefix="/brain", tags=["brain"])


@router.post("/analyze")
def analyze(request: Request, request_text: str) -> dict[str, object]:
    """Analyze a user request and return the Brain-generated goal."""
    container = getattr(request.app.state, "container", None)
    if container is None or getattr(container, "brain", None) is None:
        raise RuntimeError("Brain is not initialized")
    goal = container.brain.analyze(request_text)
    return {"request_text": request_text, "goal": goal.to_dict()}
