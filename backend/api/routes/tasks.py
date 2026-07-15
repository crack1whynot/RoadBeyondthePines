from fastapi import APIRouter

from backend.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("")
def list_tasks() -> list[str]:
    """List queued or planned tasks."""
    return TaskService().list_tasks()
