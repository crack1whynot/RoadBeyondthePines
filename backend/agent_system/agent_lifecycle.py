from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from backend.agent_system.agent import BaseAgent


class LifecycleObserver(Protocol):
    def on_state_change(self, agent: BaseAgent, previous: str, current: str) -> None:
        ...


@dataclass(slots=True)
class AgentLifecycle:
    """Tracks lifecycle transitions for agents."""

    observer: LifecycleObserver | None = None

    def transition(self, agent: BaseAgent, previous: str, current: str) -> None:
        if self.observer is not None:
            self.observer.on_state_change(agent, previous, current)
