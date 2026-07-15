from __future__ import annotations

from backend.agent_system.agent import BaseAgent
from backend.agent_system.agent_capability import AgentCapability
from backend.agent_system.agent_context import AgentContext
from backend.agent_system.agent_metadata import AgentMetadata
from backend.agent_system.agent_result import AgentResult
from backend.agent_system.agent_status import AgentStatus
from backend.agent_system.agent_task import AgentTask


class WorldAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="WorldAgent",
            capabilities=[AgentCapability(name="WorldGeneration")],
            metadata=AgentMetadata(name="WorldAgent", description="Manages world generation tasks"),
        )

    def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        return AgentResult(status=AgentStatus.IDLE, logs=[f"Handled world task: {task.description}"])


class GameplayAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="GameplayAgent",
            capabilities=[AgentCapability(name="Gameplay")],
            metadata=AgentMetadata(name="GameplayAgent", description="Handles gameplay-related tasks"),
        )

    def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        return AgentResult(status=AgentStatus.IDLE, logs=[f"Handled gameplay task: {task.description}"])


class VehicleAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="VehicleAgent",
            capabilities=[AgentCapability(name="Vehicles")],
            metadata=AgentMetadata(name="VehicleAgent", description="Handles vehicle-related tasks"),
        )

    def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        return AgentResult(status=AgentStatus.IDLE, logs=[f"Handled vehicle task: {task.description}"])


class UIAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="UIAgent",
            capabilities=[AgentCapability(name="UserInterface")],
            metadata=AgentMetadata(name="UIAgent", description="Handles UI-related tasks"),
        )

    def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        return AgentResult(status=AgentStatus.IDLE, logs=[f"Handled UI task: {task.description}"])


class AnimationAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="AnimationAgent",
            capabilities=[AgentCapability(name="Animation")],
            metadata=AgentMetadata(name="AnimationAgent", description="Handles animation-related tasks"),
        )

    def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        return AgentResult(status=AgentStatus.IDLE, logs=[f"Handled animation task: {task.description}"])


class AudioAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="AudioAgent",
            capabilities=[AgentCapability(name="Audio")],
            metadata=AgentMetadata(name="AudioAgent", description="Handles audio-related tasks"),
        )

    def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        return AgentResult(status=AgentStatus.IDLE, logs=[f"Handled audio task: {task.description}"])


class NetworkingAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="NetworkingAgent",
            capabilities=[AgentCapability(name="Networking")],
            metadata=AgentMetadata(name="NetworkingAgent", description="Handles networking-related tasks"),
        )

    def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        return AgentResult(status=AgentStatus.IDLE, logs=[f"Handled networking task: {task.description}"])


class TestingAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="TestingAgent",
            capabilities=[AgentCapability(name="Testing")],
            metadata=AgentMetadata(name="TestingAgent", description="Handles testing-related tasks"),
        )

    def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        return AgentResult(status=AgentStatus.IDLE, logs=[f"Handled testing task: {task.description}"])


class DocumentationAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="DocumentationAgent",
            capabilities=[AgentCapability(name="Documentation")],
            metadata=AgentMetadata(name="DocumentationAgent", description="Handles documentation-related tasks"),
        )

    def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        return AgentResult(status=AgentStatus.IDLE, logs=[f"Handled documentation task: {task.description}"])


class GitAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="GitAgent",
            capabilities=[AgentCapability(name="Git")],
            metadata=AgentMetadata(name="GitAgent", description="Handles git-related tasks"),
        )

    def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        return AgentResult(status=AgentStatus.IDLE, logs=[f"Handled git task: {task.description}"])


class UnrealAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="UnrealAgent",
            capabilities=[AgentCapability(name="Unreal")],
            metadata=AgentMetadata(name="UnrealAgent", description="Handles Unreal-related tasks"),
        )

    def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        return AgentResult(status=AgentStatus.IDLE, logs=[f"Handled Unreal task: {task.description}"])


class ProjectManagerAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="ProjectManagerAgent",
            capabilities=[AgentCapability(name="ProjectManagement")],
            metadata=AgentMetadata(name="ProjectManagerAgent", description="Handles project management tasks"),
        )

    def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        return AgentResult(status=AgentStatus.IDLE, logs=[f"Handled project management task: {task.description}"])
