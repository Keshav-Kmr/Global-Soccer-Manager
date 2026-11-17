"""REST snapshot save/restore."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from api_test_helpers import make_controlled_match_request, make_test_client


def test_snapshot_restore_preserves_minute_and_events():
    with make_test_client() as client:
        match_id = client.post("/matches", json=make_controlled_match_request(seed=909)).json()["match_id"]
        client.post(f"/matches/{match_id}/advance", json={"steps": 10})
        snap = client.get(f"/matches/{match_id}/snapshot").json()["snapshot"]
        assert snap["seed"] == 909
        minute_at_snap = snap["clock"]["minute"]

        client.post(f"/matches/{match_id}/advance", json={"steps": 5})
        later = client.get(f"/matches/{match_id}").json()["minute"]
        assert later > minute_at_snap

        client.post(f"/matches/{match_id}/restore", json={"snapshot": snap})
        restored = client.get(f"/matches/{match_id}").json()
        assert restored["minute"] == minute_at_snap

        events = client.get(f"/matches/{match_id}/events").json()
        assert events[0]["index"] == 0
        assert events[-1]["minute"] <= minute_at_snap


def test_wire_events_include_monotonic_index():
    with make_test_client() as client:
        match_id = client.post("/matches", json=make_controlled_match_request(seed=808)).json()["match_id"]
        client.post(f"/matches/{match_id}/advance", json={"steps": 3})
        events = client.get(f"/matches/{match_id}/events").json()
        indices = [e["index"] for e in events]
        assert indices == list(range(len(events)))