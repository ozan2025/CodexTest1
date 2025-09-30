"""Agent responsible for recommending technicians and available slots."""
from __future__ import annotations

from typing import Any, Dict, List

from backend.agents.base import BaseAgent
from backend.tools.database import HVACDatabase


class TechnicianAgent(BaseAgent):
    def __init__(self, database: HVACDatabase) -> None:
        super().__init__(
            name="TechnicianAgent",
            description="technician scheduling availability",
        )
        self._database = database

    def handle(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        technician_id = context.get("technician_id")
        if technician_id:
            technician = self._database.get_technician(technician_id)
            return {"technician": technician}

        required_skill = context.get("skill")
        matches: List[Dict[str, Any]] = []
        data = self._database._load()
        for technician in data.get("technicians", []):
            if not required_skill or required_skill in technician.get("skills", []):
                matches.append(
                    {
                        "id": technician["id"],
                        "name": technician["name"],
                        "next_availability": technician.get("availability", [])[:3],
                    }
                )
        return {"recommendations": matches}
