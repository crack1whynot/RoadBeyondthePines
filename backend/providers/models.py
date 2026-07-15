from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ProviderCapabilities:
    """Features exposed by an AI provider implementation."""

    text_generation: bool = True
    structured_output: bool = False
    streaming: bool = False

    def to_dict(self) -> dict[str, bool]:
        return {
            "text_generation": self.text_generation,
            "structured_output": self.structured_output,
            "streaming": self.streaming,
        }


@dataclass(slots=True)
class ProviderInfo:
    """Public, non-secret metadata describing an AI provider."""

    name: str
    display_name: str
    capabilities: ProviderCapabilities = field(default_factory=ProviderCapabilities)
    model: str | None = None
    available: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "capabilities": self.capabilities.to_dict(),
            "model": self.model,
            "available": self.available,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class GenerationRequest:
    """A provider-independent text-generation request."""

    prompt: str
    system_prompt: str | None = None
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GenerationResponse:
    """A provider-independent text-generation response."""

    content: str
    provider_name: str
    model: str | None = None
    finish_reason: str = "stop"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "provider_name": self.provider_name,
            "model": self.model,
            "finish_reason": self.finish_reason,
            "metadata": self.metadata,
        }
