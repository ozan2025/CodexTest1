"""FastAPI backend powering the orchestrator POC."""
from __future__ import annotations

from pathlib import Path
from typing import Dict

import requests
from fastapi import FastAPI, HTTPException

from backend.agents.customer_agent import CustomerAgent
from backend.agents.scheduler_agent import SchedulerAgent
from backend.agents.technician_agent import TechnicianAgent
from backend.models import AppointmentRequest, AppointmentResponse, OrchestrationRequest
from backend.orchestrator import Orchestrator
from backend.realtime import RealtimeSessionFactory, RealtimeSessionRequest
from backend.tools.database import load_database

app = FastAPI(title="HVAC Agentic POC")

db_path = Path(__file__).resolve().parent.parent / "data" / "hvac_db.json"
database = load_database(db_path)

orchestrator = Orchestrator(
    agents=[
        CustomerAgent(database),
        TechnicianAgent(database),
        SchedulerAgent(database),
    ]
)

realtime_factory = RealtimeSessionFactory()


def build_context(request: OrchestrationRequest) -> Dict[str, str]:
    context: Dict[str, str] = {}
    for field in ("customer_id", "technician_id", "skill", "scheduled_for", "summary"):
        value = getattr(request, field)
        if value:
            context[field] = value
    return context


@app.get("/health")
def health() -> Dict[str, str]:  # pragma: no cover - trivial route
    return {"status": "ok"}


@app.post("/orchestrate")
def orchestrate(request: OrchestrationRequest) -> Dict[str, object]:
    context = build_context(request)
    try:
        return orchestrator.route(request.task, context)
    except ValueError as exc:  # pragma: no cover - simple error handling
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/customers/{customer_id}")
def get_customer(customer_id: str) -> Dict[str, object]:
    response = CustomerAgent(database).handle("customer", {"customer_id": customer_id})
    if not response["customer"]:
        raise HTTPException(status_code=404, detail="customer_not_found")
    return response


@app.post("/appointments", response_model=AppointmentResponse)
def create_appointment(request: AppointmentRequest) -> AppointmentResponse:
    agent = SchedulerAgent(database)
    result = agent.handle("schedule", request.model_dump())
    if result["status"] == "failed":
        raise HTTPException(status_code=409, detail=result)
    return AppointmentResponse(**result)


@app.post("/realtime/session")
def create_realtime_session(request: RealtimeSessionRequest) -> Dict[str, object]:
    try:
        return realtime_factory.create_session(request)
    except HTTPException:
        raise
    except ValueError as exc:  # pragma: no cover - defensive branch
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except requests.HTTPError as exc:
        detail: Dict[str, object]
        try:
            detail = exc.response.json() if exc.response is not None else {"error": str(exc)}
        except ValueError:
            detail = {"error": exc.response.text if exc.response is not None else str(exc)}
        status = exc.response.status_code if exc.response is not None else 502
        raise HTTPException(status_code=status, detail=detail) from exc
