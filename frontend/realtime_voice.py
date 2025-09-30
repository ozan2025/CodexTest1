"""Interactive client that bridges the orchestrator with OpenAI Realtime voice."""
from __future__ import annotations

import argparse
import asyncio
import base64
import contextlib
import json
import os
from dataclasses import dataclass
from typing import Any, Dict

import requests

try:  # pragma: no cover - optional dependency
    import simpleaudio as sa
except ImportError:  # pragma: no cover - optional dependency guard
    sa = None  # type: ignore[assignment]

import websockets


BACKEND_URL = os.getenv("HVAC_BACKEND_URL", "http://localhost:8000")


def _require_audio_support() -> None:
    if sa is None:
        raise RuntimeError(
            "simpleaudio is required to play realtime responses. "
            "Install it with `pip install simpleaudio`."
        )


def _format_customer_payload(payload: Dict[str, Any]) -> str:
    customer = payload.get("customer") or {}
    history = payload.get("history") or []
    name = customer.get("name", "Unknown customer")
    lines = [f"Customer summary for {name}:"]
    if customer:
        lines.append(
            f" • Contact: {customer.get('phone')} / {customer.get('email')}"
        )
        if customer.get("address"):
            lines.append(f" • Address: {customer['address']}")
        if customer.get("preferred_window"):
            lines.append(f" • Prefers service: {customer['preferred_window']}")
    if history:
        lines.append("Recent service history:")
        for item in history[:3]:
            lines.append(
                f"   - {item.get('scheduled_for')} ({item.get('status')}): {item.get('summary')}"
            )
    else:
        lines.append("No prior service requests on record.")
    return "\n".join(lines)


def _format_scheduler_payload(payload: Dict[str, Any]) -> str:
    if payload.get("status") == "failed":
        reason = payload.get("reason", "slot unavailable")
        return f"Scheduling attempt failed because {reason}."
    request = payload.get("request") or {}
    return (
        "Appointment confirmed with technician {tech} for {slot}. Summary: {summary}."
    ).format(
        tech=request.get("technician_id", "unknown technician"),
        slot=request.get("scheduled_for", "unspecified time"),
        summary=request.get("summary", "no summary provided"),
    )


def _format_technician_payload(payload: Dict[str, Any]) -> str:
    if payload.get("technician"):
        tech = payload["technician"]
        return (
            f"Technician {tech.get('name')} is available. Next openings: "
            f"{', '.join(tech.get('availability', [])[:3]) or 'not provided'}."
        )
    recommendations = payload.get("recommendations", [])
    if not recommendations:
        return "No technicians matched the requested criteria."
    lines = ["Recommended technicians:"]
    for entry in recommendations:
        openings = ", ".join(entry.get("next_availability", []) or ["no slots listed"])
        lines.append(f" - {entry.get('name')} ({entry.get('id')}): {openings}")
    return "\n".join(lines)


def summarise_orchestrator(agent: str, payload: Dict[str, Any]) -> str:
    if agent == "CustomerAgent":
        return _format_customer_payload(payload)
    if agent == "SchedulerAgent":
        return _format_scheduler_payload(payload)
    if agent == "TechnicianAgent":
        return _format_technician_payload(payload)
    return json.dumps(payload)


def run_orchestrator(task: str) -> Dict[str, Any]:
    response = requests.post(
        f"{BACKEND_URL}/orchestrate",
        json={"task": task},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def build_contextual_message(task: str, orchestration: Dict[str, Any]) -> str:
    agent = orchestration.get("agent", "unknown agent")
    payload = orchestration.get("result", {})
    summary = summarise_orchestrator(agent, payload)
    return (
        "Customer request: {task}\n" \
        "Handled by: {agent}\n" \
        "Context for response:\n{summary}"
    ).format(task=task, agent=agent, summary=summary)


def request_realtime_session(voice: str, model: str) -> Dict[str, Any]:
    response = requests.post(
        f"{BACKEND_URL}/realtime/session",
        json={"voice": voice, "model": model},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


@dataclass
class AudioCollector:
    sample_width: int = 2
    channels: int = 1
    sample_rate: int = 24000

    def play(self, audio_bytes: bytes) -> None:
        _require_audio_support()
        wave_obj = sa.WaveObject(
            audio_bytes,
            num_channels=self.channels,
            bytes_per_sample=self.sample_width,
            sample_rate=self.sample_rate,
        )
        play_obj = wave_obj.play()
        play_obj.wait_done()


async def listen_for_events(websocket: websockets.WebSocketClientProtocol) -> None:
    collector = AudioCollector()
    text_buffer: Dict[str, str] = {}
    audio_buffer: Dict[str, bytearray] = {}

    async for message in websocket:
        event = json.loads(message)
        event_type = event.get("type")

        if event_type == "response.output_text.delta":
            response_id = event["response_id"]
            delta = event.get("delta", "")
            text_buffer.setdefault(response_id, "")
            text_buffer[response_id] += delta
        elif event_type == "response.output_text.done":
            response_id = event["response_id"]
            final_text = text_buffer.pop(response_id, "")
            if final_text:
                print(f"Assistant: {final_text}")
        elif event_type == "response.output_audio.delta":
            response_id = event["response_id"]
            audio_buffer.setdefault(response_id, bytearray())
            chunk = base64.b64decode(event.get("audio", ""))
            audio_buffer[response_id].extend(chunk)
        elif event_type == "response.completed":
            response_id = event["response_id"]
            payload = audio_buffer.pop(response_id, None)
            if payload:
                collector.play(bytes(payload))
        elif event_type == "response.error":
            print(f"[Realtime error] {event.get('error')}")
        elif event_type == "error":
            print(f"[Connection error] {event.get('error')}")


async def send_turn(
    websocket: websockets.WebSocketClientProtocol,
    task: str,
    orchestration: Dict[str, Any],
) -> None:
    contextual_message = build_contextual_message(task, orchestration)

    await websocket.send(
        json.dumps(
            {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": task,
                        }
                    ],
                },
            }
        )
    )

    await websocket.send(
        json.dumps(
            {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": contextual_message,
                        }
                    ],
                },
            }
        )
    )

    await websocket.send(
        json.dumps(
            {
                "type": "response.create",
                "response": {
                    "modalities": ["text", "audio"],
                    "instructions": (
                        "Respond with a concise spoken summary for the customer. "
                        "Confirm next steps and reference the orchestrator data."
                    ),
                },
            }
        )
    )


async def run_voice_loop(model: str, voice: str) -> None:
    session = request_realtime_session(voice=voice, model=model)
    client_secret = session["client_secret"]["value"]
    ws_url = session["session"]["url"]

    headers = {
        "Authorization": f"Bearer {client_secret}",
        "OpenAI-Beta": "realtime=v1",
    }

    async with websockets.connect(ws_url, extra_headers=headers) as websocket:
        listener = asyncio.create_task(listen_for_events(websocket))
        print("Connected to OpenAI Realtime. Type 'exit' to quit.")
        try:
            while True:
                task = input("You: ").strip()
                if not task:
                    continue
                if task.lower() in {"exit", "quit"}:
                    break
                try:
                    orchestration = run_orchestrator(task)
                except requests.HTTPError as exc:
                    detail = exc.response.text if exc.response is not None else str(exc)
                    print(f"Backend error: {detail}")
                    continue
                await send_turn(websocket, task, orchestration)
        finally:
            listener.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await listener


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bridge the HVAC orchestrator with the OpenAI Realtime Voice API",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OPENAI_REALTIME_MODEL", "gpt-4o-realtime-preview-2024-12-17"),
        help="Realtime model to request",
    )
    parser.add_argument(
        "--voice",
        default=os.getenv("OPENAI_REALTIME_VOICE", "alloy"),
        help="Voice preset to use",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(run_voice_loop(model=args.model, voice=args.voice))


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()

