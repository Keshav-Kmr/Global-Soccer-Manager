"""Interactive menu for exploring match scenarios by hand.

Pick a scenario, optionally pick a seed, and watch the possession-chain
feed print out with readable, one-line-per-event descriptions plus a final
score and a small stat line. This is a manual exploration tool, not the
real commentary system (see app/commentary/CLAUDE.md) — `_describe()`
below is a throwaway formatter just for reading this output at a glance.

Run from backend/:
    python scripts/menu.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.domain.match_context import MatchContext, Weather
from app.domain.player import Position
from app.domain.tactic import DefensiveLine, Mentality, Pressing, Tactic
from app.engine.events import EventType, MatchEvent
from app.engine.match import Match
from app.engine.match_simulator import MatchSimulator
from app.engine.summary import final_score
from _teams import build_team, make_player


def _scenario_equal_teams():
    home = build_team("home", "FC Home", overall=60)
    away = build_team("away", "FC Away", overall=60)
    return home, away


def _scenario_strong_vs_weak():
    home = build_team(
        "home", "FC Strong", overall=80,
        tactic=Tactic(mentality=Mentality.ATTACKING, pressing=Pressing.HIGH),
    )
    away = build_team(
        "away", "FC Weak", overall=45,
        tactic=Tactic(mentality=Mentality.DEFENSIVE, pressing=Pressing.LOW),
    )
    return home, away


def _scenario_star_striker():
    home = build_team("home", "FC Mediocre", overall=55)
    home.starting_xi[9] = make_player(
        "home_star", "Star Striker", Position.ST, overall=55,
        shooting=95, pace=90, dribbling=85, composure=90,
    )
    away = build_team("away", "FC Average", overall=60)
    return home, away


def _scenario_high_line_vs_pace():
    home = build_team(
        "home", "FC High Line", overall=65,
        tactic=Tactic(defensive_line=DefensiveLine.HIGH, pressing=Pressing.HIGH),
    )
    away = build_team("away", "FC Pacey Counter", overall=60)
    away.starting_xi[8] = make_player("away_w1", "Speedster L", Position.W, 60, pace=95)
    away.starting_xi[10] = make_player("away_w2", "Speedster R", Position.W, 60, pace=95)
    return home, away


def _scenario_rain():
    home = build_team("home", "FC Home", overall=65)
    away = build_team("away", "FC Away", overall=65)
    return home, away


def _run_simple(home, away, seed: int) -> None:
    _print_feed(MatchSimulator().simulate(home, away, seed=seed), home, away)


def _run_rain(home, away, seed: int) -> None:
    _print_feed(
        MatchSimulator().simulate(home, away, seed=seed, context=MatchContext(weather=Weather.RAIN)),
        home, away,
    )


def _run_with_halftime_switch(home, away, seed: int) -> None:
    """Demonstrates live control: play to halftime, change home's tactic
    AND bring on a substitute, then finish the match. Both changes are
    read live by the engine — no special plumbing needed, see
    engine/match.py's module docstring."""
    match = Match(home, away, seed=seed)

    while match.minute < 45:
        match.play_next_chain()

    print(f"\n--- HALFTIME ({match.minute}') ---")
    print(f"Score so far: {final_score(match.events, home.id, away.id)}")
    print(f"{home.name} switch from DEFENSIVE/LOW to ATTACKING/HIGH pressing,")

    match.change_tactic(home, Tactic(mentality=Mentality.ATTACKING, pressing=Pressing.HIGH))

    weak_striker = home.starting_xi[9]
    star = make_player("home_sub", "Impact Sub", Position.ST, 60, shooting=90, pace=88, dribbling=80)
    match.substitute(home, weak_striker, star)
    print(f"and bring on {star.name} for {weak_striker.name}.\n--- SECOND HALF ---")

    match.play_to_completion()
    _print_feed(match.events, home, away)


SCENARIOS = {
    "1": ("Equal teams (60 vs 60)", _scenario_equal_teams, _run_simple),
    "2": ("Strong vs weak, contrasting tactics (80 vs 45)", _scenario_strong_vs_weak, _run_simple),
    "3": ("Star striker carries a mediocre team (55+1 star vs 60)", _scenario_star_striker, _run_simple),
    "4": ("High defensive line vs pacey wingers (65 vs 60)", _scenario_high_line_vs_pace, _run_simple),
    "5": ("Rain: same two teams (65 vs 65) but in the rain", _scenario_rain, _run_rain),
    "6": ("LIVE CONTROL: switch tactics + sub at halftime (60 vs 60)", _scenario_equal_teams, _run_with_halftime_switch),
}

_EVENT_TEXT = {
    EventType.KICKOFF: "Kickoff — {team} get the ball rolling.",
    EventType.POSSESSION_PROGRESS: "{team} progress through the {phase} phase (player {player}).",
    EventType.TURNOVER: "Turnover in the {phase} phase — {team} lose it to player {player}.",
    EventType.MOMENT_OF_BRILLIANCE: "MOMENT OF BRILLIANCE from player {player}!",
    EventType.SHOT: "{team} SHOOT! Player {player} takes it on.",
    EventType.GOAL: "GOAL! {team} score through player {player}.",
    EventType.SAVE: "Saved! Kept out by the goalkeeper.",
    EventType.BLOCK: "Blocked before it reaches goal.",
    EventType.OFF_TARGET: "Off target — no danger.",
    EventType.TACTIC_CHANGE: "{team} change their tactics.",
    EventType.SUBSTITUTION: "{team} make a substitution.",
    EventType.FULL_TIME: "Full time.",
}


def _describe(event: MatchEvent) -> str:
    template = _EVENT_TEXT[event.type]
    return template.format(
        team=event.team_id or "-",
        phase=event.payload.get("phase", ""),
        player=event.player_ids[0] if event.player_ids else "?",
    )


def _print_stats(events: list[MatchEvent], home_id: str, away_id: str) -> None:
    def count(event_type: EventType, team_id: str) -> int:
        return sum(1 for e in events if e.type == event_type and e.team_id == team_id)

    print()
    print(f"{'':<20}{'HOME':>8}{'AWAY':>8}")
    for label, event_type in [
        ("Shots", EventType.SHOT),
        ("Goals", EventType.GOAL),
        ("Moments of brilliance", EventType.MOMENT_OF_BRILLIANCE),
        ("Turnovers conceded", EventType.TURNOVER),
    ]:
        print(f"{label:<20}{count(event_type, home_id):>8}{count(event_type, away_id):>8}")


def _print_feed(events: list[MatchEvent], home, away) -> None:
    for event in events:
        print(f"{event.minute:>3}' {_describe(event)}")

    score = final_score(events, home.id, away.id)
    print("-" * 50)
    print(f"FINAL SCORE: {home.name} {score[home.id]} - {score[away.id]} {away.name}")
    _print_stats(events, home.id, away.id)


def main() -> None:
    print("=== Global Soccer Manager — Match Scenario Menu ===")
    while True:
        print("\nScenarios:")
        for key, (label, _builder, _runner) in SCENARIOS.items():
            print(f"  {key}. {label}")
        print("  q. Quit")

        choice = input("\nPick a scenario: ").strip().lower()
        if choice == "q":
            break
        if choice not in SCENARIOS:
            print("Unknown option, try again.")
            continue

        seed_raw = input("Seed (blank = 42): ").strip()
        try:
            seed = int(seed_raw) if seed_raw else 42
        except ValueError:
            print(f"'{seed_raw}' isn't a number, using 42.")
            seed = 42

        label, builder, runner = SCENARIOS[choice]
        home, away = builder()
        print(f"\n{home.name} vs {away.name} — seed {seed}\n" + "-" * 50)
        runner(home, away, seed)


if __name__ == "__main__":
    main()
