"""Tiny CLI client that exercises the backend orchestrator."""
from __future__ import annotations

import json
from typing import Optional

import requests
import typer

API_URL = "http://localhost:8000"

app = typer.Typer(add_completion=False, help="HVAC Agentic POC client")


def _print_response(response: requests.Response) -> None:
    try:
        payload = response.json()
    except ValueError:
        typer.echo(response.text)
        raise typer.Exit(code=1)

    typer.echo(json.dumps(payload, indent=2))


@app.command()
def orchestrate(task: str, customer_id: Optional[str] = None, technician_id: Optional[str] = None) -> None:
    """Send an orchestration request."""

    payload = {"task": task, "customer_id": customer_id, "technician_id": technician_id}
    response = requests.post(f"{API_URL}/orchestrate", json=payload, timeout=10)
    response.raise_for_status()
    _print_response(response)


@app.command()
def customer(customer_id: str) -> None:
    response = requests.get(f"{API_URL}/customers/{customer_id}", timeout=10)
    response.raise_for_status()
    _print_response(response)


@app.command()
def schedule(
    customer_id: str,
    technician_id: str,
    scheduled_for: str,
    summary: str = ""
) -> None:
    payload = {
        "customer_id": customer_id,
        "technician_id": technician_id,
        "scheduled_for": scheduled_for,
        "summary": summary,
    }
    response = requests.post(f"{API_URL}/appointments", json=payload, timeout=10)
    response.raise_for_status()
    _print_response(response)


if __name__ == "__main__":  # pragma: no cover
    app()
