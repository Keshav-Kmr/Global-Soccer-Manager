"""Test-only helpers for building CreateMatchRequest-shaped JSON payloads,
and an app wired with a near-instant Pacer so tests don't wait out a real
90-minute-equivalent match."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.delivery.services.pacer import Pacer
from app.main import create_app

_FORMATION = ["GK", "CB", "CB", "FB", "FB", "DM", "CM", "CM", "W", "ST", "W"]

_ATTRIBUTE_NAMES = [
    "pace", "dribbling", "passing", "vision", "shooting", "tackling",
    "marking", "strength", "positioning", "aggression", "composure", "stamina", "flair",
]


def make_player_payload(player_id: str, name: str, position: str, overall: int = 60, **overrides) -> dict:
    attributes = {attr: overall for attr in _ATTRIBUTE_NAMES}
    attributes.update(overrides)
    return {"id": player_id, "name": name, "position": position, "attributes": attributes}


def make_team_payload(team_id: str, name: str, overall: int = 60) -> dict:
    starting_xi = [
        make_player_payload(f"{team_id}_{i}", f"{name} #{i}", position, overall)
        for i, position in enumerate(_FORMATION)
    ]
    return {"id": team_id, "name": name, "starting_xi": starting_xi, "bench": []}


def make_match_request(seed: int = 42) -> dict:
    return {
        "team_a": make_team_payload("home", "FC Home"),
        "team_b": make_team_payload("away", "FC Away"),
        "seed": seed,
    }


def build_test_app() -> FastAPI:
    """The real app.main.create_app(), pointed at an isolated in-memory
    SQLite database and a near-instant Pacer — so a full match completes
    in well under a second and no test leaves anything behind on disk or
    shares state with another test's database."""
    return create_app(
        database_url="sqlite+aiosqlite:///:memory:",
        pacer=Pacer(seconds_per_game_minute=0.001),
    )


def make_test_client() -> TestClient:
    return TestClient(build_test_app())
