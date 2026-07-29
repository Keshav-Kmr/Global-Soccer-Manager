"""Watch a match live over the real API/WebSocket layer, in one process.

Unlike scripts/menu.py (which calls the engine directly), this goes through
the actual HTTP + WebSocket contract a real client would use: POST /matches,
then read the WebSocket stream — with the *real* Pacer, not a test-sped-up
one, so a full match takes its genuine ~27 real seconds (45 chains x
MINUTES_PER_CHAIN x REAL_SECONDS_PER_GAME_MINUTE — see delivery/services/pacer.py).

Uses FastAPI's TestClient as an in-process ASGI client rather than needing
a second terminal running `uvicorn app.main:app` — no real server or socket
involved, but it exercises the exact same routes/schemas/WebSocket handling
a real deployment would. To point this at an actual running server instead,
swap TestClient for a real HTTP+WebSocket client (httpx + websockets)
against http://localhost:8000.

Run from backend/ (inside the venv):
    python scripts/live_client.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

from _teams import build_team
from app.domain.tactic import Mentality, Pressing, Tactic
from app.delivery.schemas import TeamSchema
from app.main import create_app


def main() -> None:
    home = build_team(
        "home", "FC Home", overall=65,
        tactic=Tactic(mentality=Mentality.ATTACKING, pressing=Pressing.HIGH),
    )
    away = build_team("away", "FC Away", overall=60)

    app = create_app()
    with TestClient(app) as client:
        response = client.post(
            "/matches",
            json={
                "team_a": TeamSchema.model_validate(home, from_attributes=True).model_dump(mode="json"),
                "team_b": TeamSchema.model_validate(away, from_attributes=True).model_dump(mode="json"),
                "seed": 42,
            },
        )
        response.raise_for_status()
        match_id = response.json()["match_id"]
        print(f"Match created: {match_id}")
        print("Connecting to the live stream (this takes about half a minute)...\n")

        with client.websocket_connect(f"/matches/{match_id}/stream") as ws:
            while True:
                message = ws.receive_json()
                print(f"{message['minute']:>3}' {message['commentary']}")
                if message["type"] == "full_time":
                    break


if __name__ == "__main__":
    main()
