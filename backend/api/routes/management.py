from fastapi import APIRouter

from backend.services.asset_service import AssetService
from backend.services.build_service import BuildService
from backend.services.git_service import GitService
from backend.services.plugin_service import PluginService
from backend.services.task_service import TaskService
from backend.services.unreal_service import UnrealService

router = APIRouter(prefix="/management", tags=["management"])


@router.get("/plugins")
def get_plugins() -> dict[str, object]:
    return {"plugins": PluginService().list_plugins()}


@router.get("/unreal")
def get_unreal_status() -> dict[str, object]:
    return UnrealService().status()


@router.get("/git")
def get_git_status() -> dict[str, object]:
    return GitService().status()


@router.get("/tasks")
def list_management_tasks() -> dict[str, object]:
    return {"tasks": TaskService().list_tasks()}


@router.get("/assets")
def get_asset_summary() -> dict[str, object]:
    return {"assets": AssetService().list_assets()}


@router.get("/build")
def get_build_summary() -> dict[str, object]:
    return {"builds": BuildService().list_builds()}
