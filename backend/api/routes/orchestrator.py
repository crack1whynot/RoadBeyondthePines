"""Compatibility endpoint for direct orchestrator requests."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from backend.orchestrator.errors import (
    InvalidOrchestrationRequestError,
    RuntimeUnavailableError,
    UnsupportedRequestError,
)

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])


@router.post("/request")
def handle_orchestrator_request(request: Request, request_text: str) -> dict[str, object]:
    """Execute a supported request without the Brain/memory application use case."""

    container = getattr(request.app.state, "container", None)
    orchestrator = getattr(container, "orchestrator", None)
    if orchestrator is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Orchestrator is not initialized",
        )
    try:
        return orchestrator.handle_request(request_text)
    except InvalidOrchestrationRequestError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except UnsupportedRequestError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    except RuntimeUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
