"""Manual test harness: build two teams with hand-set stats and tactics,
simulate a match, and print the raw event feed.

This is the tool for tuning the constants in probability.py, fatigue.py,
tactical_matchup.py, and match_simulator.py against how a match actually
plays out — run it, look at the score/shot counts, adjust, repeat.

For an interactive way to pick between several ready-made scenarios and
get readable, commented output, see menu.py in this same folder instead.

Run from backend/:
    python scripts/simulate_demo.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.domain.player import Position
from app.domain.tactic import Mentality, Pressing, Tactic
from app.engine.match_simulator import MatchSimulator
from app.engine.summary import final_score
from _teams import build_team, make_player


def main() -> None:
    # Scenario: a mediocre team (overall 55) that has one genuine star
    # striker, against an average opponent (overall 60). Shows how to give
    # a single player hand-picked stats instead of a flat team `overall`.
    mediocre = build_team(
        "home", "FC Mediocre", overall=55,
        tactic=Tactic(mentality=Mentality.BALANCED, pressing=Pressing.MEDIUM),
    )
    # Slot 9 in the 4-3-3 is the ST — replace it with a custom player.
    mediocre.starting_xi[9] = make_player(
        "home_star", "Star Striker", Position.ST, overall=55,
        shooting=95, pace=90, dribbling=85, composure=90,
    )

    average = build_team(
        "away", "FC Average", overall=60,
        tactic=Tactic(mentality=Mentality.BALANCED, pressing=Pressing.MEDIUM),
    )

    events = MatchSimulator().simulate(mediocre, average, seed=42)

    for event in events:
        print(f"{event.minute:>3}' {event.type.value:<20} team={event.team_id} players={event.player_ids}")

    print()
    print("Final score:", final_score(events, mediocre.id, average.id))


if __name__ == "__main__":
    main()
