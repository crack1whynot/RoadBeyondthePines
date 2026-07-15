from __future__ import annotations

from backend.agents.base_agent import BaseAgent


class NetworkingAgent(BaseAgent):
    """Agent focused on networking and multiplayer systems."""

    name = "NetworkingAgent"

    def run(self) -> None:
        # TODO: implement networking workflow abstraction.
        raise NotImplementedError
