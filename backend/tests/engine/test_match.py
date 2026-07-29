"""Statistical tests proving the match-context/live-control mechanics have
a real effect on outcomes, not just on paper. See backend/CLAUDE.md's
testing philosophy.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from factories import build_team, make_player

from app.domain.match_context import MatchContext, Weather
from app.domain.player import Position
from app.domain.tactic import Mentality, Pressing, Tactic
from app.engine.events import EventType
from app.engine.match import Match
from app.engine.match_simulator import MatchSimulator
from app.engine.summary import final_score

N = 300


def test_home_advantage_increases_win_rate_for_otherwise_identical_squads():
    home_wins = away_wins = 0
    for seed in range(N):
        home = build_team("home", "Home", overall=60)
        away = build_team("away", "Away", overall=60)
        events = MatchSimulator().simulate(home, away, seed=seed)
        score = final_score(events, home.id, away.id)
        if score[home.id] > score[away.id]:
            home_wins += 1
        elif score[away.id] > score[home.id]:
            away_wins += 1

    assert home_wins > away_wins


def test_rain_reduces_total_goals_compared_to_clear_weather():
    def total_goals(context: MatchContext) -> int:
        total = 0
        for seed in range(N):
            home = build_team("home", "Home", overall=65)
            away = build_team("away", "Away", overall=65)
            events = MatchSimulator().simulate(home, away, seed=seed, context=context)
            score = final_score(events, home.id, away.id)
            total += score[home.id] + score[away.id]
        return total

    clear_goals = total_goals(MatchContext(weather=Weather.CLEAR))
    rain_goals = total_goals(MatchContext(weather=Weather.RAIN))

    assert rain_goals < clear_goals


def _goals_for(events, team_id, after_minute=0):
    return sum(1 for e in events if e.type == EventType.GOAL and e.team_id == team_id and e.minute > after_minute)


def test_switching_to_an_attacking_tactic_at_halftime_increases_second_half_goals():
    def second_half_goals(switch: bool) -> int:
        total = 0
        for seed in range(N):
            home = build_team(
                "home", "Home", overall=60,
                tactic=Tactic(mentality=Mentality.DEFENSIVE, pressing=Pressing.LOW),
            )
            away = build_team("away", "Away", overall=60)
            match = Match(home, away, seed=seed)

            while match.minute < 45:
                match.play_next_chain()
            halftime_minute = match.minute

            if switch:
                match.change_tactic(home, Tactic(mentality=Mentality.ATTACKING, pressing=Pressing.HIGH))

            events = match.play_to_completion()
            total += _goals_for(events, home.id, after_minute=halftime_minute)
        return total

    without_switch = second_half_goals(switch=False)
    with_switch = second_half_goals(switch=True)

    assert with_switch > without_switch


def test_substituting_in_a_much_better_striker_increases_second_half_goals():
    def second_half_goals(substitute: bool) -> int:
        total = 0
        for seed in range(N):
            home = build_team("home", "Home", overall=55)
            away = build_team("away", "Away", overall=60)
            match = Match(home, away, seed=seed)

            while match.minute < 45:
                match.play_next_chain()
            halftime_minute = match.minute

            if substitute:
                weak_striker = home.starting_xi[9]  # ST slot in the 4-3-3 (see factories.py)
                star = make_player(
                    "home_star", "Star", Position.ST, 55,
                    shooting=95, pace=90, dribbling=85, composure=90,
                )
                match.substitute(home, weak_striker, star)

            events = match.play_to_completion()
            total += _goals_for(events, home.id, after_minute=halftime_minute)
        return total

    without_sub = second_half_goals(substitute=False)
    with_sub = second_half_goals(substitute=True)

    assert with_sub > without_sub


def test_change_tactic_and_substitute_emit_events_and_mutate_the_team_immediately():
    home = build_team("home", "Home", overall=60)
    away = build_team("away", "Away", overall=60)
    match = Match(home, away, seed=1)

    new_tactic = Tactic(mentality=Mentality.ATTACKING)
    match.change_tactic(home, new_tactic)
    assert home.tactic is new_tactic
    assert match.events[-1].type == EventType.TACTIC_CHANGE

    old_player = home.starting_xi[9]
    new_player = make_player("home_sub", "Sub", Position.ST, 70)
    match.substitute(home, old_player, new_player)
    assert home.starting_xi[9] is new_player
    assert match.events[-1].type == EventType.SUBSTITUTION
