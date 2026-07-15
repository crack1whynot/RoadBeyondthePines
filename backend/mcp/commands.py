from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable

from backend.mcp.errors import MCPCommandNotFoundError, MCPInvalidRequestError


@dataclass(frozen=True, slots=True)
class MCPCommandDefinition:
    """Static policy metadata for one supported Unreal MCP command."""

    name: str
    description: str
    read_only: bool
    required_capabilities: tuple[str, ...] = ()

    def to_dict(self, *, enabled: bool | None = None) -> dict[str, object]:
        data: dict[str, object] = {
            "name": self.name,
            "description": self.description,
            "read_only": self.read_only,
            "required_capabilities": list(self.required_capabilities),
        }
        if enabled is not None:
            data["enabled"] = enabled
        return data


DEFAULT_COMMAND_DEFINITIONS: tuple[MCPCommandDefinition, ...] = (
    MCPCommandDefinition("unreal.ping", "Check bridge responsiveness.", True),
    MCPCommandDefinition("unreal.get_connection_info", "Read bridge connection metadata.", True),
    MCPCommandDefinition(
        "unreal.get_project_info",
        "Read project metadata.",
        True,
        ("project.read",),
    ),
    MCPCommandDefinition("unreal.get_editor_state", "Read editor state.", True, ("editor.read",)),
    MCPCommandDefinition("unreal.list_maps", "List project maps.", True, ("content.read",)),
    MCPCommandDefinition(
        "unreal.get_current_map",
        "Read the current editor map.",
        True,
        ("content.read",),
    ),
    MCPCommandDefinition("unreal.list_assets", "List project assets.", True, ("content.read",)),
    MCPCommandDefinition("unreal.get_asset", "Read one asset's metadata.", True, ("content.read",)),
    MCPCommandDefinition(
        "unreal.list_plugins",
        "List enabled project plugins.",
        True,
        ("project.read",),
    ),
    MCPCommandDefinition(
        "unreal.run_python_readonly",
        "Run a registered read-only bridge action.",
        True,
        ("python.readonly",),
    ),
    MCPCommandDefinition("unreal.open_map", "Open a map in the editor.", False, ("editor.write",)),
    MCPCommandDefinition(
        "unreal.save_current_level",
        "Save the currently loaded level.",
        False,
        ("editor.write",),
    ),
    MCPCommandDefinition("unreal.save_asset", "Save an existing asset.", False, ("editor.write",)),
    MCPCommandDefinition("unreal.run_python", "Run editor Python.", False, ("python.write",)),
    MCPCommandDefinition(
        "unreal.execute_editor_command",
        "Execute an editor command.",
        False,
        ("editor.write",),
    ),
)


_ALLOWED_ARGUMENTS: dict[str, frozenset[str]] = {
    "unreal.ping": frozenset(),
    "unreal.get_connection_info": frozenset(),
    "unreal.get_project_info": frozenset(),
    "unreal.get_editor_state": frozenset(),
    "unreal.list_maps": frozenset(),
    "unreal.get_current_map": frozenset(),
    "unreal.list_assets": frozenset({"path", "class_name", "limit"}),
    "unreal.get_asset": frozenset({"object_path"}),
    "unreal.list_plugins": frozenset(),
    "unreal.run_python_readonly": frozenset({"action"}),
    "unreal.open_map": frozenset({"map_path", "object_path", "confirm_write"}),
    "unreal.save_current_level": frozenset({"confirm_write"}),
    "unreal.save_asset": frozenset({"object_path", "confirm_write"}),
    "unreal.run_python": frozenset({"confirm_write"}),
    "unreal.execute_editor_command": frozenset({"confirm_write"}),
}
_SHORT_UNREAL_NAME_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_UNREAL_CONTENT_REFERENCE_PATTERN = re.compile(r"/Game(?:/[A-Za-z0-9_.-]+)+\Z")


class CommandCatalog:
    """Central source of truth for all commands exposed by this MCP stage."""

    def __init__(
        self,
        definitions: Iterable[MCPCommandDefinition] = DEFAULT_COMMAND_DEFINITIONS,
    ) -> None:
        self._definitions = {definition.name: definition for definition in definitions}

    def contains(self, command_name: str) -> bool:
        return command_name in self._definitions

    def get(self, command_name: str) -> MCPCommandDefinition:
        definition = self._definitions.get(command_name)
        if definition is None:
            raise MCPCommandNotFoundError(f"Unknown Unreal MCP command '{command_name}'")
        return definition

    def is_read_only(self, command_name: str) -> bool:
        return self.get(command_name).read_only

    def get_description(self, command_name: str) -> str:
        return self.get(command_name).description

    def get_required_capabilities(self, command_name: str) -> list[str]:
        return list(self.get(command_name).required_capabilities)

    def list_commands(self) -> list[MCPCommandDefinition]:
        return [self._definitions[name] for name in sorted(self._definitions)]

    def validate_arguments(self, command_name: str, arguments: dict[str, Any]) -> None:
        """Apply safe, command-specific validation before transport execution."""
        self.get(command_name)
        if not isinstance(arguments, dict):
            raise MCPInvalidRequestError("Command arguments must be an object")

        allowed_arguments = _ALLOWED_ARGUMENTS[command_name]
        if set(arguments).difference(allowed_arguments):
            raise MCPInvalidRequestError("Command contains unsupported arguments")

        if command_name == "unreal.get_asset":
            self._validate_unreal_content_reference(arguments, "object_path")
        elif command_name == "unreal.list_assets":
            self._validate_list_assets_arguments(arguments)
        elif command_name == "unreal.run_python_readonly":
            self._validate_readonly_python_action(arguments)
        elif command_name == "unreal.open_map":
            self._validate_open_map_arguments(arguments)
        elif command_name == "unreal.save_asset":
            self._validate_unreal_content_reference(arguments, "object_path")

    @staticmethod
    def _require_nonempty_string(arguments: dict[str, Any], key: str) -> None:
        value = arguments.get(key)
        if not isinstance(value, str) or not value.strip():
            raise MCPInvalidRequestError(f"'{key}' must be a non-empty string")

    @staticmethod
    def _validate_list_assets_arguments(arguments: dict[str, Any]) -> None:
        if "path" in arguments:
            CommandCatalog._validate_unreal_content_reference(
                arguments,
                "path",
                allow_content_root=True,
            )
        if "class_name" in arguments:
            class_name = arguments["class_name"]
            if not isinstance(class_name, str) or not _SHORT_UNREAL_NAME_PATTERN.fullmatch(
                class_name
            ):
                raise MCPInvalidRequestError("'class_name' must be an Unreal class name")
        if "limit" in arguments:
            limit = arguments["limit"]
            if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
                raise MCPInvalidRequestError("'limit' must be a positive integer")

    @staticmethod
    def _validate_open_map_arguments(arguments: dict[str, Any]) -> None:
        targets = [key for key in ("map_path", "object_path") if key in arguments]
        if len(targets) != 1:
            raise MCPInvalidRequestError("Open map requires exactly one Unreal map target")
        CommandCatalog._validate_unreal_content_reference(
            arguments,
            targets[0],
            allow_short_name=True,
        )

    @staticmethod
    def _validate_unreal_content_reference(
        arguments: dict[str, Any],
        key: str,
        *,
        allow_short_name: bool = False,
        allow_content_root: bool = False,
    ) -> None:
        CommandCatalog._require_nonempty_string(arguments, key)
        reference = arguments[key].strip()
        normalized_segments = reference.replace("\\", "/").split("/")
        if (
            "\\" in reference
            or reference.startswith(("//", "~"))
            or bool(re.match(r"[A-Za-z]:[/\\]", reference))
            or ".." in normalized_segments
        ):
            raise MCPInvalidRequestError("Filesystem paths are not permitted")
        if allow_content_root and reference == "/Game":
            return
        if _UNREAL_CONTENT_REFERENCE_PATTERN.fullmatch(reference):
            return
        if allow_short_name and _SHORT_UNREAL_NAME_PATTERN.fullmatch(reference):
            return
        raise MCPInvalidRequestError("Path must be a virtual Unreal /Game reference")

    @staticmethod
    def _validate_readonly_python_action(arguments: dict[str, Any]) -> None:
        allowed_actions = {"get_selected_assets", "get_level_actors", "get_project_paths"}
        if set(arguments) != {"action"}:
            raise MCPInvalidRequestError("Read-only Python accepts only the 'action' argument")
        action = arguments.get("action")
        if action not in allowed_actions:
            raise MCPInvalidRequestError("Read-only Python action is not registered")
