"""Common scaffolding for all agents in the orchestrator."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Protocol


class AgentProtocol(Protocol):
    name: str
    description: str

    def can_handle(self, task: str) -> bool:
        ...

    def handle(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        ...


@dataclass
class BaseAgent:
    name: str
    description: str

    def can_handle(self, task: str) -> bool:  # pragma: no cover - simple helper
        keywords = {token.lower() for token in task.split()}
        return any(keyword in keywords for keyword in self.description.lower().split())

    def handle(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:  # pragma: no cover
        raise NotImplementedError
