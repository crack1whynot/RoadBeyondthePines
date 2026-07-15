from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from backend.mcp.commands import CommandCatalog
from backend.mcp.errors import (
    MCPCommandRejectedError,
    MCPError,
    MCPInvalidRequestError,
    MCPNotConnectedError,
    MCPUnrealError,
)
from backend.mcp.models import (
    MCPCommand,
    MCPCommandResult,
    MCPHealthStatus,
    UnrealAssetInfo,
    UnrealConnectionInfo,
    UnrealMapInfo,
    UnrealProjectInfo,
)
from backend.mcp.transport import UnrealTransport


_MOCK_PROJECT_NAME = "RoadBeyondThePines"
_MOCK_PROJECT_PATH = "C:/GameDevelopment/RoadBeyondThePines"
_MOCK_ENGINE_VERSION = "5.8"
_MOCK_LAST_SEEN = datetime(2026, 1, 1, tzinfo=timezone.utc)
_MOCK_CAPABILITIES: tuple[str, ...] = (
    "content.read",
    "editor.read",
    "project.read",
    "python.readonly",
)


@dataclass(slots=True)
class MockUnrealTransport(UnrealTransport):
    """Deterministic, offline Unreal transport for local development and tests."""

    project_path: str = _MOCK_PROJECT_PATH
    _connected: bool = field(default=False, init=False, repr=False)
    _catalog: CommandCatalog = field(default_factory=CommandCatalog, init=False, repr=False)

    async def connect(self) -> UnrealConnectionInfo:
        """Mark the offline bridge connected and return stable fixture metadata."""
        self._connected = True
        return self._connection_info()

    async def disconnect(self) -> None:
        """Mark the offline bridge disconnected without performing I/O."""
        self._connected = False

    async def is_connected(self) -> bool:
        """Return the mock transport's in-memory connection state."""
        return self._connected

    async def execute(self, command: MCPCommand) -> MCPCommandResult:
        """Execute one supported command against deterministic offline fixtures."""
        if not self._connected:
            raise MCPNotConnectedError("Mock Unreal transport is not connected")

        try:
            definition = self._catalog.get(command.name)
            self._catalog.validate_arguments(command.name, command.arguments)
            data = (
                self._execute_readonly_command(command)
                if definition.read_only
                else self._execute_write_command(command)
            )
        except MCPError as error:
            return self._error_result(command, error)

        return MCPCommandResult(
            command_id=command.id,
            success=True,
            data=data,
            duration_ms=0.0,
            metadata={"mode": "offline", "transport": self.get_name()},
        )

    async def health_check(self) -> MCPHealthStatus:
        """Return deterministic local health without contacting Unreal or a network."""
        if self._connected:
            return MCPHealthStatus(
                healthy=True,
                connected=True,
                latency_ms=0.0,
                message="Mock Unreal transport is connected",
                details={"mode": "offline", "transport": self.get_name()},
            )
        return MCPHealthStatus(
            healthy=False,
            connected=False,
            message="Mock Unreal transport is disconnected",
            details={"mode": "offline", "transport": self.get_name()},
        )

    def get_name(self) -> str:
        """Return the stable registered transport name."""
        return "mock"

    def get_capabilities(self) -> list[str]:
        """Return the read-only capabilities available from this fixture transport."""
        return list(_MOCK_CAPABILITIES)

    def _execute_readonly_command(self, command: MCPCommand) -> dict[str, Any]:
        if command.name == "unreal.ping":
            return {"message": "pong"}
        if command.name == "unreal.get_connection_info":
            return self._connection_info().to_dict()
        if command.name == "unreal.get_project_info":
            return self._project_info().to_dict()
        if command.name == "unreal.list_maps":
            return {"maps": [map_info.to_dict() for map_info in self._maps()]}
        if command.name == "unreal.get_current_map":
            return self._current_map().to_dict()
        if command.name == "unreal.list_assets":
            return self._list_assets(command.arguments)
        if command.name == "unreal.get_asset":
            return self._get_asset(command.arguments["object_path"])
        if command.name == "unreal.list_plugins":
            return {"plugins": self._plugins()}
        if command.name == "unreal.get_editor_state":
            return self._editor_state()
        if command.name == "unreal.run_python_readonly":
            return self._run_readonly_action(command.arguments["action"])
        raise MCPCommandRejectedError(
            f"Command '{command.name}' is not implemented by the mock transport"
        )

    def _connection_info(self) -> UnrealConnectionInfo:
        return UnrealConnectionInfo(
            connected=self._connected,
            transport=self.get_name(),
            engine_version=_MOCK_ENGINE_VERSION,
            project_name=_MOCK_PROJECT_NAME,
            project_path=self.project_path,
            capabilities=self.get_capabilities(),
            last_seen=_MOCK_LAST_SEEN if self._connected else None,
        )

    def _project_info(self) -> UnrealProjectInfo:
        project_root = self.project_path.rstrip("/\\")
        return UnrealProjectInfo(
            project_name=_MOCK_PROJECT_NAME,
            project_path=self.project_path,
            engine_version=_MOCK_ENGINE_VERSION,
            project_file=f"{project_root}/{_MOCK_PROJECT_NAME}.uproject",
            content_path="/Game",
            plugins=self._plugins(),
            maps=[map_info.package_path for map_info in self._maps()],
            metadata={"mode": "offline", "source": "mock"},
        )

    @staticmethod
    def _plugins() -> list[str]:
        return ["EnhancedInput", "ModelingToolsEditorMode", "Niagara"]

    @staticmethod
    def _maps() -> list[UnrealMapInfo]:
        return [
            UnrealMapInfo(
                name="L_PineRoad",
                object_path="/Game/Maps/L_PineRoad.L_PineRoad",
                package_path="/Game/Maps/L_PineRoad",
                is_current=True,
                metadata={"theme": "pine_forest"},
            ),
            UnrealMapInfo(
                name="L_ForestOutpost",
                object_path="/Game/Maps/L_ForestOutpost.L_ForestOutpost",
                package_path="/Game/Maps/L_ForestOutpost",
                metadata={"theme": "forest_outpost"},
            ),
            UnrealMapInfo(
                name="L_Prototype",
                object_path="/Game/Maps/L_Prototype.L_Prototype",
                package_path="/Game/Maps/L_Prototype",
                metadata={"theme": "prototype"},
            ),
        ]

    def _current_map(self) -> UnrealMapInfo:
        return self._maps()[0]

    @staticmethod
    def _assets() -> list[UnrealAssetInfo]:
        return [
            UnrealAssetInfo(
                object_path=(
                    "/Game/Environment/PineTrees/SM_PineTree_01.SM_PineTree_01"
                ),
                package_name="/Game/Environment/PineTrees/SM_PineTree_01",
                asset_name="SM_PineTree_01",
                asset_class="StaticMesh",
                package_path="/Game/Environment/PineTrees",
                tags={"Category": "Environment", "Theme": "Pines"},
                metadata={"source": "mock"},
            ),
            UnrealAssetInfo(
                object_path="/Game/Blueprints/BP_PineRoadGameMode.BP_PineRoadGameMode",
                package_name="/Game/Blueprints/BP_PineRoadGameMode",
                asset_name="BP_PineRoadGameMode",
                asset_class="Blueprint",
                package_path="/Game/Blueprints",
                tags={"Category": "Gameplay"},
                metadata={"source": "mock"},
            ),
            UnrealAssetInfo(
                object_path="/Game/Materials/MI_PineFog.MI_PineFog",
                package_name="/Game/Materials/MI_PineFog",
                asset_name="MI_PineFog",
                asset_class="MaterialInstanceConstant",
                package_path="/Game/Materials",
                tags={"Category": "Atmosphere", "Theme": "Pines"},
                metadata={"source": "mock"},
            ),
            UnrealAssetInfo(
                object_path=(
                    "/Game/Data/DA_RoadBeyondThePinesSettings."
                    "DA_RoadBeyondThePinesSettings"
                ),
                package_name="/Game/Data/DA_RoadBeyondThePinesSettings",
                asset_name="DA_RoadBeyondThePinesSettings",
                asset_class="DataAsset",
                package_path="/Game/Data",
                tags={"Category": "Configuration"},
                metadata={"source": "mock"},
            ),
        ]

    def _list_assets(self, arguments: dict[str, Any]) -> dict[str, Any]:
        assets = self._assets()
        path = arguments.get("path")
        if path:
            normalized_path = path.rstrip("/")
            assets = [
                asset
                for asset in assets
                if asset.package_path == normalized_path
                or asset.package_path.startswith(f"{normalized_path}/")
            ]

        class_name = arguments.get("class_name")
        if class_name:
            normalized_class_name = class_name.casefold()
            assets = [
                asset
                for asset in assets
                if asset.asset_class.casefold() == normalized_class_name
            ]

        limit = arguments.get("limit")
        if limit is not None:
            assets = assets[:limit]

        return {
            "assets": [asset.to_dict() for asset in assets],
            "total": len(assets),
        }

    def _get_asset(self, object_path: str) -> dict[str, Any]:
        for asset in self._assets():
            if asset.object_path == object_path:
                return asset.to_dict()
        raise MCPUnrealError(f"Mock asset '{object_path}' was not found")

    def _editor_state(self) -> dict[str, Any]:
        current_map = self._current_map()
        selected_assets = self._assets()[:2]
        return {
            "editor_running": True,
            "is_playing": False,
            "current_map": current_map.to_dict(),
            "selected_assets": [asset.to_dict() for asset in selected_assets],
            "level_actor_count": 4,
            "mode": "mock",
        }

    def _run_readonly_action(self, action: str) -> dict[str, Any]:
        if action == "get_selected_assets":
            return {
                "action": action,
                "selected_assets": [asset.to_dict() for asset in self._assets()[:2]],
            }
        if action == "get_level_actors":
            return {
                "action": action,
                "map": self._current_map().object_path,
                "actors": [
                    {
                        "name": "PlayerStart",
                        "class_name": "PlayerStart",
                        "label": "Player Start",
                    },
                    {
                        "name": "PineRoadLandscape",
                        "class_name": "Landscape",
                        "label": "Pine Road Landscape",
                    },
                    {
                        "name": "DirectionalLight",
                        "class_name": "DirectionalLight",
                        "label": "Sun Light",
                    },
                    {
                        "name": "ExponentialHeightFog",
                        "class_name": "ExponentialHeightFog",
                        "label": "Pine Fog",
                    },
                ],
            }
        if action == "get_project_paths":
            project = self._project_info()
            return {
                "action": action,
                "project_path": project.project_path,
                "project_file": project.project_file,
                "content_path": project.content_path,
            }
        raise MCPCommandRejectedError("Read-only Python action is not registered")

    def _execute_write_command(self, command: MCPCommand) -> dict[str, Any]:
        """Simulate only the catalogued non-dangerous editor write operations."""
        if command.name == "unreal.open_map":
            return self._open_map(command.arguments)
        if command.name == "unreal.save_current_level":
            return {
                "saved_map": self._current_map().to_dict(),
                "simulated": True,
            }
        if command.name == "unreal.save_asset":
            return self._save_asset(command.arguments)
        raise MCPCommandRejectedError(
            f"Command '{command.name}' is not available in the mock transport"
        )

    def _open_map(self, arguments: dict[str, Any]) -> dict[str, Any]:
        map_path = arguments.get("map_path", arguments.get("object_path"))
        if not isinstance(map_path, str) or not map_path.strip():
            raise MCPInvalidRequestError("'map_path' must be a non-empty string")
        normalized_path = map_path.strip()
        for map_info in self._maps():
            if normalized_path in {map_info.package_path, map_info.object_path, map_info.name}:
                return {"opened_map": map_info.to_dict(), "simulated": True}
        raise MCPUnrealError(f"Mock map '{normalized_path}' was not found")

    def _save_asset(self, arguments: dict[str, Any]) -> dict[str, Any]:
        object_path = arguments.get("object_path")
        if not isinstance(object_path, str) or not object_path.strip():
            raise MCPInvalidRequestError("'object_path' must be a non-empty string")
        asset = self._get_asset(object_path.strip())
        return {"saved_asset": asset, "simulated": True}

    def _error_result(self, command: MCPCommand, error: MCPError) -> MCPCommandResult:
        return MCPCommandResult(
            command_id=command.id,
            success=False,
            error=error.to_error_info(),
            duration_ms=0.0,
            metadata={"mode": "offline", "transport": self.get_name()},
        )
