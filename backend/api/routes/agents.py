from fastapi import APIRouter, HTTPException, Request, status

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("")
def list_agents(request: Request) -> dict[str, object]:
    """List registered agents from the new provider-independent agent system."""
    container = getattr(request.app.state, "container", None)
    if container is None or getattr(container, "agent_registry", None) is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent registry is not initialized",
        )
    agents = container.agent_registry.list_agents()
    return {"agents": [agent.get_metadata().name for agent in agents]}
