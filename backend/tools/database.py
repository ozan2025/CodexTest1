"""Utility helpers for interacting with the HVAC JSON database."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import json


@dataclass
class HVACDatabase:
    """Simple JSON-backed data store used by the agents.

    The implementation intentionally keeps things lightweight so the POC can be
    run without any external dependencies.  A real implementation could replace
    this with SQLAlchemy, a vector database, etc.
    """

    path: Path

    def _load(self) -> Dict[str, Any]:
        with self.path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write(self, payload: Dict[str, Any]) -> None:
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        data = self._load()
        return next((c for c in data.get("customers", []) if c["id"] == customer_id), None)

    def get_technician(self, technician_id: str) -> Optional[Dict[str, Any]]:
        data = self._load()
        return next((t for t in data.get("technicians", []) if t["id"] == technician_id), None)

    def list_service_requests(self, customer_id: Optional[str] = None) -> List[Dict[str, Any]]:
        data = self._load()
        requests = data.get("service_requests", [])
        if customer_id is None:
            return requests
        return [req for req in requests if req["customer_id"] == customer_id]

    def add_service_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        data = self._load()
        data.setdefault("service_requests", []).append(request)
        self._write(data)
        return request

    def reserve_slot(self, technician_id: str, slot: str) -> bool:
        data = self._load()
        updated = False
        for technician in data.get("technicians", []):
            if technician["id"] == technician_id:
                if slot in technician.get("availability", []):
                    technician["availability"].remove(slot)
                    updated = True
                break
        if updated:
            self._write(data)
        return updated


def load_database(path: str | Path) -> HVACDatabase:
    return HVACDatabase(Path(path))
