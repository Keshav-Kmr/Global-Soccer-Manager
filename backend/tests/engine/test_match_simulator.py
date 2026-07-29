"""Statistical/balance tests — validate game balance, not just code
correctness. See backend/CLAUDE.md's testing philosophy: these assert
aggregate properties across many simulations rather than one exact result.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from factories import build_team

from app.engine.match_simulator import MatchSimulator
from app.engine.summary import final_score

SIMULATIONS = 600


def _simulate_many(strong, weak):
    simulator = MatchSimulator()
    strong_wins = weak_wins = draws = 0
    total_goals = 0

    for seed in range(SIMULATIONS):
        events = simulator.simulate(strong, weak, seed=seed)
        score = final_score(events, strong.id, weak.id)
        total_goals += score[strong.id] + score[weak.id]

        if score[strong.id] > score[weak.id]:
            strong_wins += 1
        elif score[weak.id] > score[strong.id]:
            weak_wins += 1
        else:
            draws += 1

    return strong_wins, weak_wins, draws, total_goals


def test_the_stronger_team_wins_significantly_more_but_not_always():
    strong = build_team("strong", "FC Strong", overall=80)
    weak = build_team("weak", "FC Weak", overall=40)

    strong_wins, weak_wins, _, _ = _simulate_many(strong, weak)

    strong_win_rate = strong_wins / SIMULATIONS
    # Quality must matter a lot...
    assert strong_win_rate > 0.55
    # ...but never so much that the weaker team can't ever cause an upset.
    assert weak_wins > 0


def test_evenly_matched_teams_are_close_to_a_coin_flip():
    team_a = build_team("a", "FC A", overall=60)
    team_b = build_team("b", "FC B", overall=60)

    a_wins, b_wins, draws, _ = _simulate_many(team_a, team_b)

    a_win_rate = a_wins / SIMULATIONS
    assert 0.30 < a_win_rate < 0.70


def test_reproducible_from_the_same_seed():
    strong = build_team("strong", "FC Strong", overall=75)
    weak = build_team("weak", "FC Weak", overall=45)
    simulator = MatchSimulator()

    events_a = simulator.simulate(strong, weak, seed=123)
    events_b = simulator.simulate(strong, weak, seed=123)

    assert [(e.minute, e.type, e.team_id, e.player_ids) for e in events_a] == [
        (e.minute, e.type, e.team_id, e.player_ids) for e in events_b
    ]
