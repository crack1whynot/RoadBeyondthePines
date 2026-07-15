from __future__ import annotations

from backend.agents.base_agent import BaseAgent


class AudioAgent(BaseAgent):
    """Agent focused on audio systems and implementation."""

    name = "AudioAgent"

    def run(self) -> None:
        # TODO: implement audio workflow abstraction.
        raise NotImplementedError
