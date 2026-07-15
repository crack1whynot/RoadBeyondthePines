from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from backend.providers.errors import (
    ProviderConfigurationError,
    ProviderGenerationError,
    ProviderNotFoundError,
    ProviderUnavailableError,
)
from backend.providers.manager import ProviderManager
from backend.providers.models import GenerationRequest

router = APIRouter(prefix="/providers", tags=["providers"])


def _get_provider_manager(request: Request) -> ProviderManager:
    container = getattr(request.app.state, "container", None)
    manager = getattr(container, "provider_manager", None) if container is not None else None
    if manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI providers are not initialized",
        )
    return manager


def _provider_error_to_http_exception(error: Exception) -> HTTPException:
    if isinstance(error, ProviderNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, (ProviderConfigurationError, ProviderUnavailableError)):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error))
    if isinstance(error, ProviderGenerationError):
        return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="AI provider error",
    )


@router.get("")
def list_providers(request: Request) -> dict[str, object]:
    """List configured providers and their public capabilities."""
    manager = _get_provider_manager(request)
    return {"providers": [provider.to_dict() for provider in manager.list_provider_info()]}


@router.get("/active")
def get_active_provider(request: Request) -> dict[str, object]:
    """Return public metadata for the configured default provider."""
    manager = _get_provider_manager(request)
    try:
        return {"provider": manager.get_active_provider_info().to_dict()}
    except (ProviderConfigurationError, ProviderNotFoundError) as error:
        raise _provider_error_to_http_exception(error) from error


@router.post("/generate")
def generate(
    request: Request,
    generation_request: GenerationRequest,
    provider_name: str | None = None,
) -> dict[str, object]:
    """Generate text through the active provider or an explicit registered provider."""
    manager = _get_provider_manager(request)
    try:
        response = manager.generate(generation_request, provider_name=provider_name)
        return {"response": response.to_dict()}
    except (
        ProviderConfigurationError,
        ProviderGenerationError,
        ProviderNotFoundError,
        ProviderUnavailableError,
    ) as error:
        raise _provider_error_to_http_exception(error) from error
