"""End-to-end checks for clock, formations, pitch state, and statistics."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from factories import build_team, make_player

from app.domain.formation import Formation
from app.domain.player import Position
from app.domain.team import Team
from app.engine.events import EventType
from app.engine.match import Match
from app.engine.match_simulator import MatchSimulator
from app.engine.summary import final_score, team_goals_consistent


def test_full_match_happy_path_clock_pitch_and_stats():
    home = build_team("home", "Home", overall=62)
    away = build_team("away", "Away", overall=60)
    match = Match(home, away, seed=101)
    events = match.play_to_completion()

    assert match.finished
    assert any(e.type == EventType.HALF_TIME for e in events)
    assert events[-1].type == EventType.FULL_TIME
    assert events[-1].minute >= 90

    halftime = next(e for e in events if e.type == EventType.HALF_TIME)
    assert halftime.minute > 45

    kickoff = events[0]
    assert "pitch" in kickoff.payload
    assert "ball" in kickoff.payload["pitch"]

    progress = next(e for e in events if e.type == EventType.POSSESSION_PROGRESS)
    assert "pitch" in progress.payload
    assert 0 <= progress.payload["pitch"]["ball"]["x"] <= 100

    assert team_goals_consistent(events, match.statistics, home.id, away.id)
    total_chains = match.statistics.teams[home.id].possession_chains + match.statistics.teams[away.id].possession_chains
    assert total_chains > 20


def test_invalid_formation_lineup_rejected():
    players = [
        make_player(f"p{i}", f"P{i}", pos, 60)
        for i, pos in enumerate(
            [Position.GK, Position.CB, Position.CB, Position.FB, Position.FB, Position.DM, Position.CM, Position.CM, Position.W, Position.W, Position.W]
        )
    ]
    with pytest.raises(ValueError, match="slot 9"):
        Team(id="bad", name="Bad XI", starting_xi=players, formation=Formation.FOUR_THREE_THREE)


def test_deterministic_replay_after_milestone2_features():
    home = build_team("home", "Home", overall=58)
    away = build_team("away", "Away", overall=58)
    simulator = MatchSimulator()

    events_a = simulator.simulate(home, away, seed=404)
    events_b = simulator.simulate(home, away, seed=404)

    assert [(e.minute, e.type, e.team_id, e.player_ids, e.payload.get("pitch", {})) for e in events_a] == [
        (e.minute, e.type, e.team_id, e.player_ids, e.payload.get("pitch", {})) for e in events_b
    ]

    match = Match(build_team("h2", "H2", 60), build_team("a2", "A2", 60), seed=777)
    match.play_to_completion()
    derived = final_score(match.events, match.team_a.id, match.team_b.id)
    assert derived[match.team_a.id] == match.statistics.teams[match.team_a.id].goals