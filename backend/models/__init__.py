"""Pydantic models shared by the backend."""
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional


class OrchestrationRequest(BaseModel):
    task: str = Field(..., description="Natural language description of the task")
    customer_id: Optional[str] = None
    technician_id: Optional[str] = None
    skill: Optional[str] = None
    scheduled_for: Optional[str] = None
    summary: Optional[str] = None


class AppointmentRequest(BaseModel):
    customer_id: str
    technician_id: str
    scheduled_for: str
    summary: str = ""


class AppointmentResponse(BaseModel):
    status: str
    request: Optional[dict] = None
    reason: Optional[str] = None
