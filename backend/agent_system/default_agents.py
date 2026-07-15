from __future__ import annotations

from typing import Any

from backend.agent_system.agent import BaseAgent
from backend.agent_system.agent_capability import AgentCapability
from backend.agent_system.agent_context import AgentContext
from backend.agent_system.agent_metadata import AgentMetadata
from backend.agent_system.agent_result import AgentResult
from backend.agent_system.agent_task import AgentTask
from backend.core.execution import ExecutionStatus


class DiagnosticAgent(BaseAgent):
    """A local, deterministic agent used to verify the execution pipeline."""

    def __init__(self) -> None:
        super().__init__(
            name="DiagnosticAgent",
            capabilities=[
                AgentCapability(name="diagnostic.execute"),
                AgentCapability(name="system.echo"),
            ],
            metadata=AgentMetadata(
                name="DiagnosticAgent",
                description="Echoes an explicitly supplied local payload for pipeline diagnostics",
                priority=100,
            ),
        )

    def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        if task.cancellation_token:
            return AgentResult.failed(
                task_id=task.task_id,
                agent_id=self.name,
                error="Task was cancelled before diagnostic execution",
                code="TASK_CANCELLED",
                status=ExecutionStatus.CANCELLED,
            )

        # This is a real local operation: the caller's payload is returned
        # unchanged.  When no dedicated payload is supplied, the supplied
        # parameter object itself is the diagnostic payload.
        payload: Any = task.parameters.get("payload", task.parameters)
        return AgentResult.succeeded(
            task_id=task.task_id,
            agent_id=self.name,
            output=payload,
            metadata={"operation": "echo"},
        )


class NotImplementedAgent(BaseAgent):
    """Explicit failure boundary for built-ins without an implementation."""

    def __init__(self, *, name: str, capability: str, description: str) -> None:
        super().__init__(
            name=name,
            capabilities=[AgentCapability(name=capability)],
            metadata=AgentMetadata(name=name, description=description),
        )
        self._capability = capability

    def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        if task.cancellation_token:
            return AgentResult.failed(
                task_id=task.task_id,
                agent_id=self.name,
                error="Task was cancelled before agent execution",
                code="TASK_CANCELLED",
                status=ExecutionStatus.CANCELLED,
            )
        return AgentResult.failed(
            task_id=task.task_id,
            agent_id=self.name,
            error=f"{self.name} is not implemented in the current execution pipeline",
            code="NOT_IMPLEMENTED",
            metadata={"capability": self._capability},
        )


class WorldAgent(NotImplementedAgent):
    def __init__(self) -> None:
        super().__init__(
            name="WorldAgent",
            capability="WorldGeneration",
            description="Reserved for world generation tasks",
        )


class GameplayAgent(NotImplementedAgent):
    def __init__(self) -> None:
        super().__init__(
            name="GameplayAgent",
            capability="Gameplay",
            description="Reserved for gameplay tasks",
        )


class VehicleAgent(NotImplementedAgent):
    def __init__(self) -> None:
        super().__init__(
            name="VehicleAgent",
            capability="Vehicles",
            description="Reserved for vehicle tasks",
        )


class UIAgent(NotImplementedAgent):
    def __init__(self) -> None:
        super().__init__(
            name="UIAgent",
            capability="UserInterface",
            description="Reserved for user-interface tasks",
        )


class AnimationAgent(NotImplementedAgent):
    def __init__(self) -> None:
        super().__init__(
            name="AnimationAgent",
            capability="Animation",
            description="Reserved for animation tasks",
        )


class AudioAgent(NotImplementedAgent):
    def __init__(self) -> None:
        super().__init__(
            name="AudioAgent",
            capability="Audio",
            description="Reserved for audio tasks",
        )


class NetworkingAgent(NotImplementedAgent):
    def __init__(self) -> None:
        super().__init__(
            name="NetworkingAgent",
            capability="Networking",
            description="Reserved for networking tasks",
        )


class TestingAgent(NotImplementedAgent):
    def __init__(self) -> None:
        super().__init__(
            name="TestingAgent",
            capability="Testing",
            description="Reserved for test-execution tasks",
        )


class DocumentationAgent(NotImplementedAgent):
    def __init__(self) -> None:
        super().__init__(
            name="DocumentationAgent",
            capability="Documentation",
            description="Reserved for documentation tasks",
        )


class GitAgent(NotImplementedAgent):
    def __init__(self) -> None:
        super().__init__(
            name="GitAgent",
            capability="Git",
            description="Reserved for Git tasks",
        )


class UnrealAgent(NotImplementedAgent):
    """A future MCP-backed agent; the injected port is intentionally unused."""

    def __init__(self, mcp_manager: object | None = None) -> None:
        self._mcp_manager = mcp_manager
        super().__init__(
            name="UnrealAgent",
            capability="Unreal",
            description="Reserved for Unreal MCP-backed tasks",
        )

    def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        result = super().execute(task, context)
        result.metadata["mcp_port_configured"] = self._mcp_manager is not None
        return result


class ProjectManagerAgent(NotImplementedAgent):
    def __init__(self) -> None:
        super().__init__(
            name="ProjectManagerAgent",
            capability="ProjectManagement",
            description="Reserved for project-management tasks",
        )
