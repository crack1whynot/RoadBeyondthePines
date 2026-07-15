"""Application use case for the Phase 0 Brain-to-execution handoff."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from backend.brain.brain import Brain
from backend.core.logging import get_logger
from backend.memory.memory import ProjectMemory
from backend.memory.memory_entry import MemoryEntry
from backend.orchestrator.orchestrator import Orchestrator

logger = get_logger("services.development_request")

_SENSITIVE_VALUE = re.compile(
    r"(?i)\b(api[_-]?key|auth(?:orization)?|token|password|secret)\b\s*[:=]\s*(?:bearer\s+)?[^\s,;\"']+"
)
_SENSITIVE_KEY_PARTS = ("api_key", "apikey", "authorization", "token", "password", "secret")


@dataclass(slots=True)
class DevelopmentRequestService:
    """Coordinate Brain analysis, execution, and best-effort memory storage."""

    brain: Brain
    orchestrator: Orchestrator
    memory: ProjectMemory | None = None

    def execute(self, request_text: str) -> dict[str, Any]:
        """Execute a request without treating memory failures as task failures."""

        request_id = str(uuid4())
        goal = self.brain.analyze(request_text)
        execution = self.orchestrator.execute_goal(goal)
        memory_persisted = False
        warnings: list[str] = []

        if self.memory is None:
            warnings.append("MEMORY_UNAVAILABLE")
        else:
            try:
                entry = self._build_memory_entry(request_id, goal.to_dict(), execution)
                self.memory.store_entry(entry)
                memory_persisted = True
            except Exception as error:  # Memory is explicitly best-effort in Phase 0.
                logger.warning(
                    "Execution summary persistence failed for request %s: %s",
                    request_id,
                    type(error).__name__,
                )
                warnings.append("MEMORY_PERSISTENCE_FAILED")

        return {
            "request_id": request_id,
            "goal": goal.to_dict(),
            "execution": execution,
            "warnings": warnings,
            "metadata": {"memory_persisted": memory_persisted},
        }

    @classmethod
    def _build_memory_entry(
        cls,
        request_id: str,
        goal: dict[str, Any],
        execution: dict[str, Any],
    ) -> MemoryEntry:
        plan = execution.get("plan", {})
        results = execution.get("results", {})
        task_summaries = [
            cls._task_summary(result)
            for result in results.get("results", [])
            if isinstance(result, dict)
        ]
        summary = {
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "goal": {
                "id": goal.get("id"),
                "description": cls._sanitize_value(goal.get("description")),
                "required_capabilities": list(goal.get("required_capabilities", [])),
            },
            "execution_plan": {
                "id": plan.get("id"),
                "status": plan.get("status"),
                "task_count": len(plan.get("tasks", [])),
            },
            "task_results": task_summaries,
        }
        return MemoryEntry(
            id=f"execution-{request_id}",
            title="Execution pipeline summary",
            category="execution",
            tags=["execution", "phase-0"],
            content=json.dumps(summary, ensure_ascii=False, sort_keys=True),
            source="development_request_service",
            metadata={
                "request_id": request_id,
                "plan_id": plan.get("id"),
                "final_status": plan.get("status"),
            },
        )

    @classmethod
    def _task_summary(cls, result: dict[str, Any]) -> dict[str, Any]:
        return {
            "task_id": result.get("task_id"),
            "agent_id": result.get("agent_id"),
            "status": result.get("status"),
            "success": bool(result.get("success")),
            "error_code": result.get("error_code"),
            "error": cls._sanitize_value(result.get("error")),
            "output": cls._sanitize_value(result.get("output")),
        }

    @staticmethod
    def _sanitize_value(value: Any) -> str | None:
        if value is None:
            return None
        value = DevelopmentRequestService._redact_structure(value)
        try:
            text = json.dumps(value, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            text = str(value)
        text = _SENSITIVE_VALUE.sub(lambda match: f"{match.group(1)}=[REDACTED]", text)
        return text[:1024]

    @classmethod
    def _redact_structure(cls, value: Any) -> Any:
        """Redact secret-shaped mapping values before serialising a summary."""

        if isinstance(value, Mapping):
            redacted: dict[str, Any] = {}
            for key, item in value.items():
                key_text = str(key)
                normalized_key = key_text.casefold().replace("-", "_")
                if any(part in normalized_key for part in _SENSITIVE_KEY_PARTS):
                    redacted[key_text] = "[REDACTED]"
                else:
                    redacted[key_text] = cls._redact_structure(item)
            return redacted
        if isinstance(value, (list, tuple, set)):
            return [cls._redact_structure(item) for item in value]
        if isinstance(value, str):
            return _SENSITIVE_VALUE.sub(
                lambda match: f"{match.group(1)}=[REDACTED]",
                value,
            )
        return value
