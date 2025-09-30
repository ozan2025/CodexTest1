"""Helpers for creating OpenAI Realtime voice sessions."""
from __future__ import annotations

import os
from typing import Any, Dict, List

import requests
from pydantic import BaseModel, Field


DEFAULT_REALTIME_MODEL = "gpt-4o-realtime-preview-2024-12-17"
DEFAULT_VOICE = "alloy"


class RealtimeSessionRequest(BaseModel):
    """Payload expected by the ``/realtime/session`` endpoint."""

    model: str = Field(
        default=DEFAULT_REALTIME_MODEL,
        description="OpenAI Realtime model to use for the session.",
    )
    voice: str = Field(
        default=DEFAULT_VOICE,
        description="Voice preset to use for spoken responses.",
    )
    instructions: str | None = Field(
        default=None,
        description="Optional custom instructions for the voice assistant.",
    )


class RealtimeSessionFactory:
    """Factory that exchanges the server-side API key for an ephemeral token."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1/realtime/sessions",
    ) -> None:
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._base_url = base_url

    @staticmethod
    def _default_instructions() -> str:
        return (
            "You are the friendly voice for Northwind HVAC. "
            "Converse naturally, collect the customer's intent, and explain "
            "the results produced by the backend orchestrator in everyday "
            "language."
        )

    @staticmethod
    def _tool_schemas() -> List[Dict[str, Any]]:
        """Tool descriptions mirrored by ``frontend.realtime_voice``."""

        return [
            {
                "type": "function",
                "name": "orchestrate_task",
                "description": (
                    "Route a natural-language task through the HVAC orchestrator "
                    "to retrieve data or schedule follow-up work."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string"},
                        "customer_id": {"type": "string"},
                        "technician_id": {"type": "string"},
                        "skill": {"type": "string"},
                        "scheduled_for": {"type": "string"},
                        "summary": {"type": "string"},
                    },
                    "required": ["task"],
                },
            }
        ]

    def create_session(self, request: RealtimeSessionRequest) -> Dict[str, Any]:
        """Create a short-lived session description for browser clients."""

        if not self._api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not configured; cannot create realtime session"
            )

        payload: Dict[str, Any] = {
            "model": request.model,
            "voice": request.voice,
            "instructions": request.instructions or self._default_instructions(),
            "modalities": ["text", "audio"],
            "tools": self._tool_schemas(),
            "input_audio_format": {"codec": "pcm16", "sample_rate": 16000},
            "output_audio_format": {"codec": "pcm16", "sample_rate": 24000},
        }

        response = requests.post(
            self._base_url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "OpenAI-Beta": "realtime=v1",
            },
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()


__all__ = ["RealtimeSessionFactory", "RealtimeSessionRequest"]

