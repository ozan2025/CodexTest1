"""Agent that surfaces customer insights."""
from __future__ import annotations

from typing import Any, Dict

from backend.agents.base import BaseAgent
from backend.tools.database import HVACDatabase


class CustomerAgent(BaseAgent):
    def __init__(self, database: HVACDatabase) -> None:
        super().__init__(
            name="CustomerAgent",
            description="customer profile contact preferences",
        )
        self._database = database

    def handle(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        customer_id = context.get("customer_id")
        if not customer_id:
            raise ValueError("customer_id is required for customer lookups")
        customer = self._database.get_customer(customer_id)
        history = self._database.list_service_requests(customer_id)
        return {"customer": customer, "history": history}
