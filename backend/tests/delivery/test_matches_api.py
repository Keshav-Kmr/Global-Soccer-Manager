"""FastAPI TestClient tests for the delivery layer.

Every test wraps its whole body in `with make_test_client() as client:` —
not just the WebSocket part. MatchService.start_match() schedules the match
simulation as a background asyncio task; TestClient only keeps a single
persistent event loop alive (able to actually run that background task
concurrently with the test) when used as a context manager for the full
flow. Outside a `with` block, each call gets its own short-lived loop and
the background task is torn down with it — the WebSocket then polls
forever for events that will never arrive.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest
from starlette.websockets import WebSocketDisconnect

from api_test_helpers import make_match_request, make_test_client


def test_create_match_returns_a_match_id():
    with make_test_client() as client:
        response = client.post("/matches", json=make_match_request())

        assert response.status_code == 200
        match_id = response.json()["match_id"]
        assert isinstance(match_id, str) and match_id


def test_unknown_match_id_closes_the_websocket():
    with make_test_client() as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/matches/does-not-exist/stream"):
                pass


def test_stream_delivers_kickoff_then_full_time_with_commentary():
    with make_test_client() as client:
        match_id = client.post("/matches", json=make_match_request()).json()["match_id"]

        messages = []
        with client.websocket_connect(f"/matches/{match_id}/stream") as ws:
            while True:
                message = ws.receive_json()
                messages.append(message)
                if message["type"] == "full_time":
                    break

        assert messages[0]["type"] == "kickoff"
        assert messages[-1]["type"] == "full_time"
        # Every message is fully-formed wire shape, with commentary attached
        # — not a bare re-serialization of the internal MatchEvent.
        for message in messages:
            assert set(message) == {"index", "minute", "type", "team", "players", "payload", "commentary"}
            assert isinstance(message["commentary"], str) and message["commentary"]


def test_two_viewers_of_the_same_match_see_the_same_events():
    """Proves the engine runs once per match, not once per viewer — both
    connections read from the same growing event log."""
    with make_test_client() as client:
        match_id = client.post("/matches", json=make_match_request(seed=7)).json()["match_id"]

        def collect_all_events():
            events = []
            with client.websocket_connect(f"/matches/{match_id}/stream") as ws:
                while True:
                    message = ws.receive_json()
                    events.append(message)
                    if message["type"] == "full_time":
                        break
            return events

        first_viewer_events = collect_all_events()
        second_viewer_events = collect_all_events()

        assert first_viewer_events == second_viewer_events


def test_a_late_viewer_gets_the_full_backlog_then_the_rest_live():
    with make_test_client() as client:
        match_id = client.post("/matches", json=make_match_request()).json()["match_id"]

        # Let the match run to completion server-side before connecting at all.
        with client.websocket_connect(f"/matches/{match_id}/stream") as ws:
            while ws.receive_json()["type"] != "full_time":
                pass

        # A brand-new, "late" viewer must still get the entire match from the top.
        with client.websocket_connect(f"/matches/{match_id}/stream") as ws:
            first_message = ws.receive_json()
            assert first_message["type"] == "kickoff"


def test_match_result_is_available_only_after_the_match_finishes():
    """The durable record (persistence/match_result_repository.py) — not
    to be confused with the live in-memory session /stream reads from."""
    with make_test_client() as client:
        match_id = client.post("/matches", json=make_match_request()).json()["match_id"]

        before = client.get(f"/matches/{match_id}/result")
        assert before.status_code == 404

        with client.websocket_connect(f"/matches/{match_id}/stream") as ws:
            while ws.receive_json()["type"] != "full_time":
                pass

        after = client.get(f"/matches/{match_id}/result")
        assert after.status_code == 200
        body = after.json()
        assert body["match_id"] == match_id
        assert isinstance(body["score_a"], int) and isinstance(body["score_b"], int)
        assert len(body["events"]) > 0


def test_unknown_match_result_is_404():
    with make_test_client() as client:
        response = client.get("/matches/does-not-exist/result")
        assert response.status_code == 404
