"""Brain analysis and the explicit Phase 0 execution use case."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from backend.orchestrator.errors import (
    InvalidOrchestrationRequestError,
    RuntimeUnavailableError,
    UnsupportedRequestError,
)
from backend.services.development_request_service import DevelopmentRequestService

router = APIRouter(prefix="/brain", tags=["brain"])


class DevelopmentExecuteRequest(BaseModel):
    """Validated body for the real diagnostic execution path."""

    request_text: str = Field(min_length=1, max_length=10_000)


def _get_development_service(request: Request) -> DevelopmentRequestService:
    container = getattr(request.app.state, "container", None)
    service = getattr(container, "development_request_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Development execution is not initialized",
        )
    return service


@router.post("/analyze")
def analyze(request: Request, request_text: str) -> dict[str, object]:
    """Analyze only; this endpoint never queues or executes work."""

    container = getattr(request.app.state, "container", None)
    brain = getattr(container, "brain", None)
    if brain is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Brain is not initialized",
        )
    goal = brain.analyze(request_text)
    return {"request_text": request_text, "goal": goal.to_dict()}


@router.post("/execute")
def execute(request: Request, payload: DevelopmentExecuteRequest) -> dict[str, object]:
    """Run Brain → Orchestrator → Runtime for a supported diagnostic request."""

    service = _get_development_service(request)
    try:
        return service.execute(payload.request_text)
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
