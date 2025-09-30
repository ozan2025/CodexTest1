# HVAC Agentic POC

This proof of concept shows how an orchestrator agent can coordinate specialised
sub-agents and simple tools to support a fictitious HVAC servicing company.  It
uses a lightweight FastAPI backend and a Python CLI frontend so everything can
run locally without extra services.

## Project layout

```
backend/
  app.py               FastAPI application exposing the orchestrator endpoints
  orchestrator.py      Lightweight router that delegates to sub agents
  agents/              Customer, technician, and scheduler agent implementations
  tools/database.py    JSON-backed data access helper used by the agents
frontend/
  cli.py               Typer-based CLI that talks to the backend API
```

The data store lives at [`data/hvac_db.json`](data/hvac_db.json) and can be
edited directly to seed additional technicians, customers, or service history.

## Running the backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app:app --reload
```

Once the server is running you can interact with it through the interactive
[Swagger UI](http://localhost:8000/docs) or by using the CLI client.

## Using the CLI frontend

With the backend running in another terminal:

```bash
source .venv/bin/activate
python -m frontend.cli orchestrate "customer profile" --customer-id CUST-001
python -m frontend.cli customer CUST-001
python -m frontend.cli schedule CUST-001 TECH-101 2024-06-16T10:30:00 "Seasonal tune-up"
```

## Using the OpenAI Realtime Voice bridge

The backend now exposes ``POST /realtime/session`` which exchanges your server
side ``OPENAI_API_KEY`` for an ephemeral client secret.  This enables browser or
CLI clients to establish short-lived WebRTC/WebSocket sessions with the OpenAI
Realtime API without exposing the production key.

1. Export your OpenAI key and start the backend:

   ```bash
   export OPENAI_API_KEY=sk-...
   uvicorn backend.app:app --reload
   ```

2. Ensure the realtime voice dependencies (``simpleaudio`` and ``websockets``)
   are installed. They are included in ``requirements.txt`` but can also be
   installed separately if you are using a different environment:

   ```bash
   pip install simpleaudio websockets
   ```

3. Launch the realtime bridge which routes user intents through the JSON-backed
   orchestrator and streams the response back as both text and speech:

   ```bash
   python -m frontend.realtime_voice
   ```

   Type a request such as ``Find a technician for a heat pump tune up`` and the
   assistant will call the orchestrator, summarise the result, and speak the
   answer using OpenAI's realtime voice synthesis.

The implementation in ``frontend/realtime_voice.py`` can be extended further to
capture microphone audio, surface tool call metadata, or drive a graphical UI.
Refer to the official
[OpenAI Realtime documentation](https://platform.openai.com/docs/guides/realtime)
for details on enabling two-way audio streaming or WebRTC transports.
