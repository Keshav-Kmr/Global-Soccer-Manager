"""Statistical distribution tests — tolerances set from measured batch output (100+ seeds)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from factories import build_team

from app.engine.batch_analysis import run_batch
from app.engine.match import Match
from app.engine.match_simulator import MatchSimulator
from app.engine.match_snapshot import export_snapshot, restore_snapshot


BATCH_SIZE = 120


def _report():
    home = build_team("cal_home", "Cal Home", overall=62)
    away = build_team("cal_away", "Cal Away", overall=62)
    return run_batch(home, away, count=BATCH_SIZE, seed_start=1000)


def test_batch_goal_and_shot_distributions_in_expected_bands():
    report = _report()
    data = report.to_dict()
    goals_mean = data["goals_per_match"]["mean"]
    shots_mean = data["shots_per_match"]["mean"]
    assert 1.8 <= goals_mean <= 4.5, f"goals/match mean out of band: {goals_mean}"
    assert 4.0 <= shots_mean <= 11.5, f"shots/match mean out of band: {shots_mean}"


def test_home_advantage_and_possession_passing_metrics():
    report = _report()
    data = report.to_dict()
    assert data["home_goals_per_match"] >= data["away_goals_per_match"] * 0.95
    assert data["home_win_rate"] >= 0.35
    assert 46.0 <= data["home_possession_pct_mean"] <= 54.0
    assert 48.0 <= data["pass_completion_pct_mean"] <= 72.0


def test_fouls_and_cards_per_match():
    report = _report()
    data = report.to_dict()
    assert 6.0 <= data["fouls_per_match"]["mean"] <= 16.0
    assert 2.0 <= data["cards_per_match"]["mean"] <= 8.0


def test_deterministic_replay_and_snapshot_resume():
    home = build_team("snap_h", "Snap H", 60)
    away = build_team("snap_a", "Snap A", 60)
    seed = 4242

    reference = Match(home, away, seed=seed)
    for _ in range(28):
        reference.play_next_chain()
    snap = export_snapshot(reference)
    finished_reference = Match(home, away, seed=seed)
    finished_reference_events = finished_reference.play_to_completion()

    resumed = Match(home, away, seed=seed)
    restore_snapshot(resumed, snap)
    resumed_events = list(resumed.events)
    while not resumed.finished:
        resumed.play_next_chain()
        resumed_events = list(resumed.events)

    baseline = [(e.minute, e.type, e.team_id, e.player_ids) for e in finished_reference_events]
    from_snap = [(e.minute, e.type, e.team_id, e.player_ids) for e in resumed_events]
    assert from_snap == baseline

    different_seed = Match(home, away, seed=seed + 1).play_to_completion()
    assert [
        (e.minute, e.type, e.team_id, e.player_ids) for e in different_seed
    ] != baseline


def test_simulator_matches_direct_match_for_same_seed():
    home = build_team("d_h", "D H", 58)
    away = build_team("d_a", "D A", 58)
    seed = 77
    via_sim = MatchSimulator().simulate(home, away, seed=seed)
    via_match = Match(home, away, seed=seed).play_to_completion()
    assert [(e.minute, e.type, e.team_id, e.player_ids) for e in via_sim] == [
        (e.minute, e.type, e.team_id, e.player_ids) for e in via_match
    ]