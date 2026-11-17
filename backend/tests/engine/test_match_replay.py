"""Engine-level replay with manager actions."""

from factories import build_team

from app.domain.tactic import Mentality, Pressing, Tactic
from app.engine.match_replay import ReplayAction, run_replay
from app.engine.match_simulator import MatchSimulator


def test_replay_without_actions_matches_simulator():
    home = build_team("r_h", "R H", 59)
    away = build_team("r_a", "R A", 61)
    seed = 31415
    direct = MatchSimulator().simulate(home, away, seed=seed)
    replayed = run_replay(home, away, seed).events
    assert [(e.minute, e.type, e.team_id) for e in direct] == [
        (e.minute, e.type, e.team_id) for e in replayed
    ]


def test_replay_action_at_minute_is_reproducible():
    home = build_team("act_h", "Act H", 60)
    away = build_team("act_a", "Act A", 60)
    action = ReplayAction(
        at_minute=20,
        kind="tactic_change",
        team_id=home.id,
        tactic=Tactic(mentality=Mentality.ATTACKING, pressing=Pressing.HIGH),
    )
    first = run_replay(home, away, 12001, actions=[action])
    second = run_replay(home, away, 12001, actions=[action])
    assert [(e.minute, e.type) for e in first.events] == [(e.minute, e.type) for e in second.events]