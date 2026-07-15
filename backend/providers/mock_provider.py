from __future__ import annotations

from dataclasses import dataclass, field

from backend.providers.base import AIProvider
from backend.providers.errors import ProviderUnavailableError
from backend.providers.models import (
    GenerationRequest,
    GenerationResponse,
    ProviderCapabilities,
    ProviderInfo,
)


@dataclass(slots=True)
class MockProvider(AIProvider):
    """Deterministic offline provider for local development and tests."""

    response_prefix: str = "Mock response: "
    model_name: str = "mock-model"
    available: bool = True
    requests: list[GenerationRequest] = field(default_factory=list)

    @property
    def name(self) -> str:
        return "mock"

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            name=self.name,
            display_name="Mock Provider",
            capabilities=ProviderCapabilities(text_generation=True),
            model=self.model_name,
            available=self.is_available(),
            metadata={"mode": "offline"},
        )

    def is_available(self) -> bool:
        return self.available

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        if not self.is_available():
            raise ProviderUnavailableError(self.name)

        self.requests.append(request)
        return GenerationResponse(
            content=f"{self.response_prefix}{request.prompt}",
            provider_name=self.name,
            model=request.model or self.model_name,
            metadata={"mode": "offline", "request_count": len(self.requests)},
        )
