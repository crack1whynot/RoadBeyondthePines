from __future__ import annotations

from dataclasses import dataclass

from backend.brain.goal import Goal


@dataclass(slots=True)
class GoalManager:
    """Stores and manages the goals created by the Brain layer."""

    _goals: list[Goal] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self._goals is None:
            self._goals = []

    def add_goal(self, goal: Goal) -> None:
        self._goals.append(goal)

    def list_goals(self) -> list[Goal]:
        return list(self._goals)
