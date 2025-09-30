"""Agent that books appointments and updates the JSON database."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from backend.agents.base import BaseAgent
from backend.tools.database import HVACDatabase


class SchedulerAgent(BaseAgent):
    def __init__(self, database: HVACDatabase) -> None:
        super().__init__(
            name="SchedulerAgent",
            description="schedule appointment booking",
        )
        self._database = database

    def handle(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        customer_id = context["customer_id"]
        technician_id = context["technician_id"]
        slot = context["scheduled_for"]
        summary = context.get("summary", "")

        if not self._database.reserve_slot(technician_id, slot):
            return {"status": "failed", "reason": "slot_unavailable"}

        request_id = f"REQ-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        payload = {
            "id": request_id,
            "customer_id": customer_id,
            "technician_id": technician_id,
            "status": "scheduled",
            "summary": summary,
            "scheduled_for": slot,
        }
        self._database.add_service_request(payload)
        return {"status": "scheduled", "request": payload}
