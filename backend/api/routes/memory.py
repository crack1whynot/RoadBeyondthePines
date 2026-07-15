from fastapi import APIRouter, Request

from backend.memory.memory_entry import MemoryEntry
from backend.memory.memory_query import MemoryQuery

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("/entries")
def create_entry(request: Request, entry: MemoryEntry) -> dict[str, object]:
    """Store a memory entry."""
    container = getattr(request.app.state, "container", None)
    if container is None or getattr(container, "memory", None) is None:
        raise RuntimeError("Memory is not initialized")
    stored = container.memory.store_entry(entry)
    return {"entry": stored.to_dict()}


@router.get("/entries")
def list_entries(request: Request) -> dict[str, object]:
    """List stored memory entries."""
    container = getattr(request.app.state, "container", None)
    if container is None or getattr(container, "memory", None) is None:
        raise RuntimeError("Memory is not initialized")
    return {"entries": [entry.to_dict() for entry in container.memory.list_entries()]}


@router.get("/search")
def search_entries(request: Request, category: str | None = None, tag: str | None = None, author: str | None = None, date: str | None = None) -> dict[str, object]:
    """Search memory entries by common filters."""
    container = getattr(request.app.state, "container", None)
    if container is None or getattr(container, "memory", None) is None:
        raise RuntimeError("Memory is not initialized")
    query = MemoryQuery(category=category, tag=tag, author=author, date=date)
    return {"entries": [entry.to_dict() for entry in container.memory.search_entries(query)]}
