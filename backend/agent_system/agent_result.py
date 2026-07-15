from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.agent_system.agent_status import AgentStatus


@dataclass(slots=True)
class AgentResult:
    """Structured result returned from an agent execution."""

    status: AgentStatus
    logs: list[str] = field(default_factory=list)
    generated_artifacts: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "logs": self.logs,
            "generated_artifacts": self.generated_artifacts,
            "warnings": self.warnings,
            "errors": self.errors,
            "metrics": self.metrics,
            "execution_time": self.execution_time,
        }
