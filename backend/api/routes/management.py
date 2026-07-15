from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

router = APIRouter(prefix="/management", tags=["management"])


def _container(request: Request) -> object:
    container = getattr(request.app.state, "container", None)
    if container is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Application services are not initialized",
        )
    return container


@router.get("/plugins")
def get_plugins(request: Request) -> dict[str, object]:
    service = getattr(_container(request), "plugin_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Plugin service is not initialized",
        )
    return {"plugins": service.list_plugins()}


@router.get("/unreal")
async def get_unreal_status(request: Request) -> dict[str, object]:
    """Return management status from the single DI-managed Unreal service."""

    service = getattr(_container(request), "unreal_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unreal service is not initialized",
        )
    return await service.status_async()


@router.get("/git")
def get_git_status(request: Request) -> dict[str, object]:
    service = getattr(_container(request), "git_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Git service is not initialized",
        )
    return service.status()


@router.get("/tasks")
def list_management_tasks(request: Request) -> dict[str, object]:
    service = getattr(_container(request), "task_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Task service is not initialized",
        )
    return {"tasks": service.list_tasks()}


@router.get("/assets")
def get_asset_summary(request: Request) -> dict[str, object]:
    service = getattr(_container(request), "asset_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Asset service is not initialized",
        )
    return {"assets": service.list_assets()}


@router.get("/build")
def get_build_summary(request: Request) -> dict[str, object]:
    service = getattr(_container(request), "build_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Build service is not initialized",
        )
    return {"builds": service.list_builds()}
