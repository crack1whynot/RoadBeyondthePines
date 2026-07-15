from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

from backend.mcp.commands import CommandCatalog, MCPCommandDefinition
from backend.mcp.errors import MCPCommandRejectedError, MCPPermissionError
from backend.mcp.models import MCPCommand, is_sensitive_key

_DANGEROUS_WRITE_COMMANDS = {"unreal.run_python", "unreal.execute_editor_command"}
_FORBIDDEN_EXECUTION_PATTERN = re.compile(
    r"(?i)(?:\b(?:powershell|cmd(?:\.exe)?|bash|sh|zsh|fish|subprocess|popen)\b|"
    r"\bos\.(?:system|popen)\b|shell\s*=\s*true)"
)
_FORBIDDEN_ARGUMENT_KEYS = {
    "command",
    "code",
    "executable",
    "powershell",
    "shell",
    "subprocess",
    "script",
}
_SECRET_VALUE_PATTERN = re.compile(r"(?i)(api[_-]?key|authorization|password|secret|token)\s*[:=]")
_FILESYSTEM_PATH_KEYS = {"file_path", "filesystem_path"}
_UNREAL_REFERENCE_KEYS = {
    "path",
    "object_path",
    "map_path",
    "package_path",
    "project_path",
    "content_path",
}


@dataclass(slots=True)
class MCPSecurityPolicy:
    """Policy that permits only catalogued, safe Unreal MCP commands."""

    catalog: CommandCatalog = field(default_factory=CommandCatalog)
    allow_write: bool = False
    allowed_project_path: str | None = None

    def validate(self, command: MCPCommand) -> MCPCommandDefinition:
        """Validate a command and return its authoritative catalog definition."""
        definition = self.catalog.get(command.name)
        self.catalog.validate_arguments(command.name, command.arguments)
        self._reject_secret_metadata(command.metadata)
        self._reject_forbidden_execution_terms(command.arguments)
        self._validate_file_paths(command.arguments)

        if not definition.read_only:
            if not self.allow_write:
                raise MCPPermissionError("Unreal MCP write commands are disabled")
            if definition.name in _DANGEROUS_WRITE_COMMANDS:
                raise MCPCommandRejectedError(
                    f"Command '{definition.name}' is not available in Unreal MCP Foundation"
                )
            if command.arguments.get("confirm_write") is not True:
                raise MCPPermissionError("Write commands require confirm_write=true")
        return definition

    def is_enabled(self, definition: MCPCommandDefinition) -> bool:
        """Return whether the current policy would permit this catalogued command."""
        if definition.read_only:
            return True
        return self.allow_write and definition.name not in _DANGEROUS_WRITE_COMMANDS

    @staticmethod
    def _reject_secret_metadata(metadata: Mapping[str, Any]) -> None:
        for key, value in metadata.items():
            if is_sensitive_key(key):
                raise MCPPermissionError("Command metadata must not contain secrets")
            if isinstance(value, Mapping):
                MCPSecurityPolicy._reject_secret_metadata(value)
            elif isinstance(value, (list, tuple)):
                for nested_value in value:
                    if isinstance(nested_value, Mapping):
                        MCPSecurityPolicy._reject_secret_metadata(nested_value)
                    elif (
                        isinstance(nested_value, str)
                        and _SECRET_VALUE_PATTERN.search(nested_value)
                    ):
                        raise MCPPermissionError("Command metadata must not contain secrets")
            elif isinstance(value, str) and _SECRET_VALUE_PATTERN.search(value):
                raise MCPPermissionError("Command metadata must not contain secrets")

    @staticmethod
    def _reject_forbidden_execution_terms(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, nested_value in value.items():
                if str(key).lower().replace("-", "_") in _FORBIDDEN_ARGUMENT_KEYS:
                    raise MCPPermissionError("Shell and subprocess execution are not permitted")
                MCPSecurityPolicy._reject_forbidden_execution_terms(nested_value)
        elif isinstance(value, (list, tuple)):
            for nested_value in value:
                MCPSecurityPolicy._reject_forbidden_execution_terms(nested_value)
        elif isinstance(value, str) and _FORBIDDEN_EXECUTION_PATTERN.search(value):
            raise MCPPermissionError("Shell and subprocess execution are not permitted")

    def _validate_file_paths(self, value: Any, *, key: str | None = None) -> None:
        """Deny native file paths unless a future catalog explicitly scopes them."""
        if isinstance(value, Mapping):
            for nested_key, nested_value in value.items():
                self._validate_file_paths(nested_value, key=str(nested_key))
            return
        if isinstance(value, (list, tuple)):
            for nested_value in value:
                self._validate_file_paths(nested_value, key=key)
            return
        if key is None:
            return

        normalized_key = key.lower().replace("-", "_")
        if normalized_key in _FILESYSTEM_PATH_KEYS:
            self._validate_allowed_filesystem_path(value)
        elif (
            normalized_key in _UNREAL_REFERENCE_KEYS
            and isinstance(value, str)
            and self._looks_like_native_filesystem_path(value)
        ):
            raise MCPPermissionError("Filesystem paths are not permitted for Unreal references")

    def _validate_allowed_filesystem_path(self, value: Any) -> None:
        if not isinstance(value, str) or not self.allowed_project_path:
            raise MCPPermissionError("Filesystem access is not permitted")
        candidate = Path(value).resolve(strict=False)
        project_root = Path(self.allowed_project_path).resolve(strict=False)
        try:
            candidate.relative_to(project_root)
        except ValueError as error:
            raise MCPPermissionError("Filesystem path is outside the Unreal project") from error

    @staticmethod
    def _looks_like_native_filesystem_path(value: str) -> bool:
        reference = value.strip()
        normalized_segments = reference.replace("\\", "/").split("/")
        return (
            "\\" in reference
            or reference.startswith(("//", "~"))
            or bool(re.match(r"[A-Za-z]:[/\\]", reference))
            or ".." in normalized_segments
            or (reference.startswith("/") and not reference.startswith("/Game"))
        )
