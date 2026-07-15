from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from backend.core.execution import ExecutionStatus

_SENSITIVE_ERROR_VALUE = re.compile(
    r"(?i)\b(api[_-]?key|auth(?:orization)?|token|password|secret)\b\s*[:=]\s*(?:bearer\s+)?[^\s,;\"']+"
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _duration_ms(started_at: datetime, finished_at: datetime) -> int:
    return max(0, int((finished_at - started_at).total_seconds() * 1000))


def _safe_error_message(value: object | None, fallback: str) -> str:
    """Return an API-safe, bounded error message.

    Agent exceptions are intentionally logged by the dispatcher, not exposed
    through this DTO.  Explicit agent errors still pass through this narrow
    normalisation so that accidental tracebacks are not returned to callers.
    """

    if value is None:
        return fallback

    message = str(value).strip()
    if not message or "traceback" in message.casefold() or "\n" in message:
        return fallback
    return _SENSITIVE_ERROR_VALUE.sub(
        lambda match: f"{match.group(1)}=[REDACTED]",
        message,
    )[:512]


@dataclass(slots=True)
class AgentResult:
    """Actual outcome of an agent task, separate from agent lifecycle state."""

    task_id: str = ""
    agent_id: str = ""
    status: ExecutionStatus = ExecutionStatus.PENDING
    output: Any = None
    error: str | None = None
    started_at: datetime = field(default_factory=_utcnow)
    finished_at: datetime | None = None
    duration_ms: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # Compatibility-only diagnostic fields retained for callers that still
    # inspect them.  New agents must use ``output`` and ``error`` instead.
    logs: list[str] = field(default_factory=list)
    generated_artifacts: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0

    def __post_init__(self) -> None:
        """Keep completion timing and compatibility error fields coherent."""

        if not isinstance(self.status, ExecutionStatus):
            self.status = ExecutionStatus(self.status)
        self.metadata = dict(self.metadata or {})
        self.logs = list(self.logs or [])
        self.generated_artifacts = list(self.generated_artifacts or [])
        self.warnings = list(self.warnings or [])
        self.errors = list(self.errors or [])
        self.metrics = dict(self.metrics or {})
        if self.error is None and self.errors:
            self.error = _safe_error_message(self.errors[0], "Agent execution failed")
        elif self.error is not None:
            self.error = _safe_error_message(self.error, "Agent execution failed")
        if self.finished_at is not None and self.duration_ms is None:
            self.duration_ms = _duration_ms(self.started_at, self.finished_at)

    @property
    def success(self) -> bool:
        """True only for a completed successful execution."""

        return self.status is ExecutionStatus.SUCCEEDED

    @property
    def error_code(self) -> str | None:
        """Stable domain error code, when this result is not successful."""

        value = self.metadata.get("error_code")
        return str(value) if value is not None else None

    def complete(self, status: ExecutionStatus, *, error: object | None = None) -> None:
        """Mark this result terminal using the actual completion time."""

        self.status = ExecutionStatus(status)
        self.finished_at = _utcnow()
        self.duration_ms = _duration_ms(self.started_at, self.finished_at)
        if status is ExecutionStatus.SUCCEEDED:
            self.error = None
            self.errors.clear()
        else:
            self.error = _safe_error_message(error or self.error, "Agent execution failed")
            self.errors = [self.error]

    @classmethod
    def succeeded(
        cls,
        *,
        task_id: str,
        agent_id: str,
        output: Any,
        started_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Build a terminal, successful result for an actual operation."""

        started = started_at or _utcnow()
        finished = _utcnow()
        return cls(
            task_id=task_id,
            agent_id=agent_id,
            status=ExecutionStatus.SUCCEEDED,
            output=output,
            started_at=started,
            finished_at=finished,
            duration_ms=_duration_ms(started, finished),
            metadata=dict(metadata or {}),
        )

    @classmethod
    def failed(
        cls,
        *,
        task_id: str,
        agent_id: str = "",
        error: object | None = None,
        code: str = "AGENT_EXECUTION_FAILED",
        started_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
        status: ExecutionStatus = ExecutionStatus.FAILED,
    ) -> AgentResult:
        """Build a terminal failure without exposing implementation details."""

        if status not in {
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.TIMED_OUT,
        }:
            raise ValueError("Failure result requires a terminal non-success status")
        started = started_at or _utcnow()
        finished = _utcnow()
        safe_error = _safe_error_message(error, "Agent execution failed")
        result_metadata = dict(metadata or {})
        result_metadata.setdefault("error_code", code)
        return cls(
            task_id=task_id,
            agent_id=agent_id,
            status=status,
            error=safe_error,
            started_at=started,
            finished_at=finished,
            duration_ms=_duration_ms(started, finished),
            metadata=result_metadata,
            errors=[safe_error],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "status": self.status.value,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "error_code": self.error_code,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": self.duration_ms,
            "metadata": dict(self.metadata),
            "logs": self.logs,
            "generated_artifacts": self.generated_artifacts,
            "warnings": self.warnings,
            "errors": self.errors,
            "metrics": self.metrics,
            "execution_time": self.execution_time,
        }
