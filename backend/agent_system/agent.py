from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from backend.agent_system.agent_context import AgentContext
from backend.agent_system.agent_status import AgentStatus
from backend.agent_system.agent_capability import AgentCapability
from backend.agent_system.agent_metadata import AgentMetadata
from backend.agent_system.agent_result import AgentResult
from backend.agent_system.agent_task import AgentTask
from backend.core.logging import get_logger

logger = get_logger("agent_system.agent")


class BaseAgent(ABC):
    """Abstract base class for provider-independent agents."""

    def __init__(self, name: str, capabilities: list[AgentCapability] | None = None, metadata: AgentMetadata | None = None) -> None:
        self.name = name
        self.capabilities = capabilities or []
        self.metadata = metadata or AgentMetadata(name=name)
        self.status = AgentStatus.IDLE
        self._logger = logger

    def initialize(self) -> None:
        self.status = AgentStatus.INITIALIZING
        self._logger.info("Initializing agent %s", self.name)

    def start(self) -> None:
        self.status = AgentStatus.IDLE
        self._logger.info("Starting agent %s", self.name)

    def stop(self) -> None:
        self.status = AgentStatus.OFFLINE
        self._logger.info("Stopping agent %s", self.name)

    def pause(self) -> None:
        self.status = AgentStatus.PAUSED
        self._logger.info("Pausing agent %s", self.name)

    def resume(self) -> None:
        self.status = AgentStatus.IDLE
        self._logger.info("Resuming agent %s", self.name)

    def cancel(self) -> None:
        self.status = AgentStatus.OFFLINE
        self._logger.info("Cancelling agent %s", self.name)

    def health_check(self) -> bool:
        return self.status not in {AgentStatus.OFFLINE, AgentStatus.ERROR}

    def get_capabilities(self) -> list[AgentCapability]:
        return list(self.capabilities)

    def get_metadata(self) -> AgentMetadata:
        return self.metadata

    @abstractmethod
    def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        raise NotImplementedError
