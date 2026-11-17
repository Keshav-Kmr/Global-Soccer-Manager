"""API tests for controlled match manager commands."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from api_test_helpers import make_controlled_match_request, make_test_client

from app.domain.formation import Formation


def test_controlled_match_only_progresses_when_advanced():
    with make_test_client() as client:
        match_id = client.post("/matches", json=make_controlled_match_request(seed=11)).json()["match_id"]

        state = client.get(f"/matches/{match_id}").json()
        assert state["mode"] == "controlled"
        assert state["minute"] == 0
        assert state["paused"] is False
        assert state["finished"] is False

        events = client.get(f"/matches/{match_id}/events").json()
        assert len(events) == 1
        assert events[0]["type"] == "kickoff"

        adv = client.post(f"/matches/{match_id}/advance", json={"steps": 3}).json()
        assert adv["advanced_chains"] == 3
        assert adv["minute"] > 0

        events_after = client.get(f"/matches/{match_id}/events").json()
        assert len(events_after) > len(events)


def test_pause_blocks_advance_then_manager_commands_emit_events():
    with make_test_client() as client:
        match_id = client.post("/matches", json=make_controlled_match_request(seed=22)).json()["match_id"]
        home_id = client.get(f"/matches/{match_id}").json()["team_a_id"]

        client.post(f"/matches/{match_id}/pause")
        blocked = client.post(f"/matches/{match_id}/advance", json={"steps": 1})
        assert blocked.status_code == 409

        client.post(f"/matches/{match_id}/resume")
        client.post(
            f"/matches/{match_id}/tactics",
            json={
                "team_id": home_id,
                "tactic": {"mentality": "attacking", "pressing": "high"},
            },
        )
        striker_out = make_controlled_match_request()["team_a"]["starting_xi"][9]["id"]
        client.post(
            f"/matches/{match_id}/substitutions",
            json={"team_id": home_id, "player_out_id": striker_out, "player_in_id": "home_sub0"},
        )
        client.post(
            f"/matches/{match_id}/formation",
            json={"team_id": home_id, "formation": Formation.FOUR_THREE_THREE.value},
        )

        types = {e["type"] for e in client.get(f"/matches/{match_id}/events").json()}
        assert "tactic_change" in types
        assert "substitution" in types
        assert "formation_change" in types

        client.post(f"/matches/{match_id}/advance", json={"steps": 1})
        stats = client.get(f"/matches/{match_id}/statistics").json()
        assert "teams" in stats and home_id in stats["teams"]


def test_controlled_websocket_receives_events_after_advance():
    with make_test_client() as client:
        match_id = client.post("/matches", json=make_controlled_match_request(seed=33)).json()["match_id"]
        client.post(f"/matches/{match_id}/advance", json={"steps": 2})

        rest_count = len(client.get(f"/matches/{match_id}/events").json())
        assert rest_count > 1

        with client.websocket_connect(f"/matches/{match_id}/stream") as ws:
            first = ws.receive_json()
            second = ws.receive_json()
        assert first["type"] == "kickoff"
        assert second["type"] != "kickoff"
        assert len({first["minute"], second["minute"]}) >= 1