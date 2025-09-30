"""High level orchestrator that dispatches work to specialised agents."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List

from backend.agents.base import AgentProtocol


class Orchestrator:
    def __init__(self, agents: Iterable[AgentProtocol]) -> None:
        self._agents: List[AgentProtocol] = list(agents)

    def route(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Route a task to the first capable agent.

        The router is intentionally simple for the POC but the API mirrors what a
        more advanced, LLM-powered orchestrator would look like.
        """

        for agent in self._agents:
            if agent.can_handle(task):
                return {
                    "agent": agent.name,
                    "result": agent.handle(task, context),
                }
        raise ValueError(f"No agent could handle task: {task}")
