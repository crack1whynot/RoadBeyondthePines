from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
import re
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

_SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "password",
    "secret",
    "token",
    "credential",
    "private_key",
    "access_key",
    "client_secret",
    "cookie",
    "session",
)
_SENSITIVE_EXACT_KEYS = {"auth", "jwt", "signature"}
_INTERNAL_KEY_PARTS = ("stack", "traceback", "trace", "debug", "internal")
_SENSITIVE_TEXT_PATTERN = re.compile(
    r"(?i)\b(?:api[_ -]?key|apikey|authorization|password|secret|token|"
    r"credential(?:s)?|bearer|access[_ -]?(?:token|key)|client[_ -]?secret|"
    r"private[_ -]?key|cookie|session(?:[_ -]?id)?)\b"
)
_INTERNAL_TEXT_PATTERN = re.compile(
    r"(?i)(?:\btraceback\b|\bstack\s*trace\b|\btrace\s*:)"
)
_RAW_SECRET_VALUE_PATTERN = re.compile(
    r"(?i)\b(?:sk-[a-z0-9_-]{8,}|gh[pousr]_[a-z0-9]{8,}|"
    r"eyJ[a-z0-9_-]{8,}\.[a-z0-9_-]{8,}\.[a-z0-9_-]{8,})\b"
)


def is_sensitive_key(key: object) -> bool:
    """Return whether a mapping key can hold a credential or secret."""
    normalized = str(key).lower().replace("-", "_")
    return normalized in _SENSITIVE_EXACT_KEYS or any(
        part in normalized for part in _SENSITIVE_KEY_PARTS
    )


def sanitize_public_text(value: str) -> str:
    """Return untrusted text without credentials or internal traceback detail."""
    if _INTERNAL_TEXT_PATTERN.search(value):
        return "[redacted internal error]"
    if _SENSITIVE_TEXT_PATTERN.search(value) or _RAW_SECRET_VALUE_PATTERN.search(value):
        return "[redacted sensitive value]"
    return value


def sanitize_public_value(value: Any) -> Any:
    """Remove secret values and stack traces from data returned by the MCP layer."""
    if isinstance(value, Mapping):
        safe: dict[str, Any] = {}
        for key, nested_value in value.items():
            normalized_key = str(key).lower().replace("-", "_")
            if is_sensitive_key(key):
                safe[str(key)] = "[redacted]"
            elif any(part in normalized_key for part in _INTERNAL_KEY_PARTS):
                continue
            else:
                safe[str(key)] = sanitize_public_value(nested_value)
        return safe
    if isinstance(value, list):
        return [sanitize_public_value(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_public_value(item) for item in value]
    if isinstance(value, str):
        return sanitize_public_text(value)
    if isinstance(value, bytes):
        return "[redacted binary data]"
    return value


def sanitize_error_message(message: str) -> str:
    """Return a short public error message without common credential patterns."""
    return sanitize_public_text(message)


class MCPModel(BaseModel):
    """Strict base model with JSON-safe serialization helpers."""

    model_config = ConfigDict(extra="forbid")

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class MCPCommand(MCPModel):
    """A provider-neutral command sent to an Unreal MCP transport."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: float | None = Field(default=None, gt=0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    read_only: bool = True
    request_id: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("Command name must not be empty")
        return name


class MCPErrorInfo(MCPModel):
    """Safe, serializable information about an MCP error."""

    code: str
    message: str
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)

    @field_validator("code", "message")
    @classmethod
    def validate_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("MCP error text must not be empty")
        return sanitize_error_message(text)

    @field_validator("details")
    @classmethod
    def sanitize_details(cls, value: dict[str, Any]) -> dict[str, Any]:
        return sanitize_public_value(value)


class MCPCommandResult(MCPModel):
    """Normalized result of one MCP command execution."""

    command_id: str
    success: bool
    data: Any | None = None
    error: MCPErrorInfo | None = None
    duration_ms: float | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("data", mode="before")
    @classmethod
    def sanitize_data(cls, value: Any) -> Any:
        return sanitize_public_value(value)

    @field_validator("metadata")
    @classmethod
    def sanitize_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        return sanitize_public_value(value)


class UnrealConnectionInfo(MCPModel):
    """Public state of the configured Unreal Editor bridge connection."""

    connected: bool
    transport: str
    engine_version: str | None = None
    project_name: str | None = None
    project_path: str | None = None
    editor_pid: int | None = Field(default=None, ge=1)
    capabilities: list[str] = Field(default_factory=list)
    last_seen: datetime | None = None

    @field_validator("transport", "engine_version", "project_name", "project_path", mode="before")
    @classmethod
    def sanitize_text_fields(cls, value: Any) -> Any:
        return sanitize_public_value(value) if isinstance(value, str) else value

    @field_validator("capabilities", mode="before")
    @classmethod
    def sanitize_capabilities(cls, value: Any) -> Any:
        if isinstance(value, list):
            return [sanitize_public_value(item) for item in value]
        return value


class UnrealProjectInfo(MCPModel):
    """Public Unreal project metadata returned by a bridge."""

    project_name: str
    project_path: str
    engine_version: str
    project_file: str
    content_path: str
    plugins: list[str] = Field(default_factory=list)
    maps: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "project_name",
        "project_path",
        "engine_version",
        "project_file",
        "content_path",
        mode="before",
    )
    @classmethod
    def sanitize_text_fields(cls, value: Any) -> Any:
        return sanitize_public_value(value) if isinstance(value, str) else value

    @field_validator("plugins", "maps", mode="before")
    @classmethod
    def sanitize_text_lists(cls, value: Any) -> Any:
        if isinstance(value, list):
            return [sanitize_public_value(item) for item in value]
        return value

    @field_validator("metadata")
    @classmethod
    def sanitize_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        return sanitize_public_value(value)


class UnrealAssetInfo(MCPModel):
    """Public metadata for one Unreal asset."""

    object_path: str
    package_name: str
    asset_name: str
    asset_class: str
    package_path: str
    tags: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "object_path",
        "package_name",
        "asset_name",
        "asset_class",
        "package_path",
        mode="before",
    )
    @classmethod
    def sanitize_text_fields(cls, value: Any) -> Any:
        return sanitize_public_value(value) if isinstance(value, str) else value

    @field_validator("tags", "metadata")
    @classmethod
    def sanitize_mappings(cls, value: dict[str, Any]) -> dict[str, Any]:
        return sanitize_public_value(value)


class UnrealMapInfo(MCPModel):
    """Public metadata for one Unreal map."""

    name: str
    object_path: str
    package_path: str
    is_current: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name", "object_path", "package_path", mode="before")
    @classmethod
    def sanitize_text_fields(cls, value: Any) -> Any:
        return sanitize_public_value(value) if isinstance(value, str) else value

    @field_validator("metadata")
    @classmethod
    def sanitize_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        return sanitize_public_value(value)


class MCPHealthStatus(MCPModel):
    """Health information exposed by an MCP transport or manager."""

    healthy: bool
    connected: bool
    latency_ms: float | None = Field(default=None, ge=0)
    message: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)

    @field_validator("message")
    @classmethod
    def sanitize_optional_message(cls, value: str | None) -> str | None:
        return sanitize_error_message(value) if value is not None else None

    @field_validator("details")
    @classmethod
    def sanitize_details(cls, value: dict[str, Any]) -> dict[str, Any]:
        return sanitize_public_value(value)


class MCPExecuteRequest(MCPModel):
    """Narrow public API input for command execution."""

    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("Command name must not be empty")
        return name
