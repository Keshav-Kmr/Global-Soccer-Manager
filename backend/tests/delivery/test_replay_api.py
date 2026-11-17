"""REST replay and verify-replay endpoints."""

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from api_test_helpers import make_controlled_match_request, make_test_client


def test_headless_replay_is_deterministic():
    with make_test_client() as client:
        body = make_controlled_match_request(seed=777)
        first = client.post("/matches/replay", json=body).json()
        second = client.post("/matches/replay", json=body).json()
        assert first["score_a"] == second["score_a"]
        assert first["score_b"] == second["score_b"]
        assert first["event_count"] == second["event_count"]
        sig1 = [(e["minute"], e["type"], e["team"]) for e in first["events"]]
        sig2 = [(e["minute"], e["type"], e["team"]) for e in second["events"]]
        assert sig1 == sig2


def test_verify_replay_against_finished_match():
    with make_test_client() as client:
        payload = make_controlled_match_request(seed=888)
        match_id = client.post("/matches", json={**payload, "mode": "controlled"}).json()["match_id"]
        client.post(f"/matches/{match_id}/advance", json={"until_finished": True})
        verify = client.post(f"/matches/{match_id}/replay", json=payload).json()
        assert verify["found_stored_result"] is True
        assert verify["score_matches"] is True
        assert verify["event_signature_matches"] is True


def test_replay_with_tactic_action_changes_outcome():
    with make_test_client() as client:
        payload = make_controlled_match_request(seed=999)
        baseline = client.post("/matches/replay", json=payload).json()
        changed = copy.deepcopy(payload)
        home_id = payload["team_a"]["id"]
        changed["actions"] = [
            {
                "at_minute": 12,
                "action": "tactic_change",
                "team_id": home_id,
                "tactic": {"mentality": "attacking", "pressing": "high"},
            }
        ]
        with_actions = client.post("/matches/replay", json=changed).json()
        same_seed_replay = client.post("/matches/replay", json=payload).json()
        assert same_seed_replay["score_a"] == baseline["score_a"]
        assert (with_actions["score_a"], with_actions["score_b"]) != (
            baseline["score_a"],
            baseline["score_b"],
        ) or with_actions["event_count"] != baseline["event_count"]


def test_duplicate_player_ids_rejected_on_create():
    with make_test_client() as client:
        body = make_controlled_match_request(seed=1)
        body["team_b"]["starting_xi"][0]["id"] = body["team_a"]["starting_xi"][0]["id"]
        response = client.post("/matches", json=body)
        assert response.status_code == 400