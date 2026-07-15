from fastapi import APIRouter, HTTPException, Request, status

from backend.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _get_task_service(request: Request) -> TaskService:
    container = getattr(request.app.state, "container", None)
    service = getattr(container, "task_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Task service is not initialized",
        )
    return service


@router.get("")
def list_tasks(request: Request) -> list[dict[str, object]]:
    """List legacy task-service records with a truthful response annotation."""

    return _get_task_service(request).list_tasks()
