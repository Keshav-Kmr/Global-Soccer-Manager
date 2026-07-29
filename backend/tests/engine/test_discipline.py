"""Statistical tests proving fouls/cards/injuries actually fire during a
full match and have the right consequences — not just that the isolated
check classes work in unit tests. See backend/CLAUDE.md testing philosophy.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from factories import build_team

from app.engine.events import EventType, MatchEvent
from app.engine.match import Match
from app.engine.match_simulator import MatchSimulator

N = 200


def _of_type(events: list[MatchEvent], event_type: EventType) -> list[MatchEvent]:
    return [e for e in events if e.type == event_type]


def test_fouls_cards_and_injuries_all_occur_over_many_matches():
    home = build_team("home", "Home", overall=60)
    away = build_team("away", "Away", overall=60)
    simulator = MatchSimulator()

    fouls = cards = injuries = 0
    for seed in range(N):
        events = simulator.simulate(home, away, seed=seed)
        fouls += len(_of_type(events, EventType.FOUL))
        cards += len(_of_type(events, EventType.CARD))
        injuries += len(_of_type(events, EventType.INJURY))

    assert fouls > 0
    assert cards > 0
    assert injuries > 0
    # Injuries are meant to be much rarer than fouls.
    assert injuries < fouls


def test_a_foul_means_the_attacking_team_keeps_the_ball():
    """A foul is a free kick, not a turnover: the team that was attacking
    when the foul happened must still be the one attacking in the next
    chain — no flip, unlike a clean turnover. Checked directly against
    Match's internal possession tracking rather than by inferring it from
    event.team_id, whose meaning differs by event type (attacking team for
    POSSESSION_PROGRESS/TURNOVER, but the *fouling* team for FOUL/CARD)."""
    home = build_team("home", "Home", overall=60)
    away = build_team("away", "Away", overall=60)

    checked_at_least_one = False

    for seed in range(N):
        match = Match(home, away, seed=seed)
        while not match.finished:
            attacker_before = match._possession
            result = match.play_next_chain()
            if any(e.type == EventType.FOUL for e in result.events):
                assert match._possession is attacker_before
                checked_at_least_one = True

    assert checked_at_least_one


def test_red_cards_are_rarer_than_yellow_cards():
    home = build_team("home", "Home", overall=60)
    away = build_team("away", "Away", overall=60)
    simulator = MatchSimulator()

    yellows = reds = 0
    for seed in range(N):
        events = simulator.simulate(home, away, seed=seed)
        for card_event in _of_type(events, EventType.CARD):
            if card_event.payload["color"] == "yellow":
                yellows += 1
            else:
                reds += 1

    assert yellows > 0
    assert reds < yellows


def test_second_yellow_becomes_a_red_card():
    home = build_team("home", "Home", overall=60)
    away = build_team("away", "Away", overall=60)
    simulator = MatchSimulator()

    found_second_yellow_case = False

    for seed in range(N):
        events = simulator.simulate(home, away, seed=seed)
        yellow_counts: dict[str, int] = {}

        for card_event in _of_type(events, EventType.CARD):
            player_id = card_event.player_ids[0]
            color = card_event.payload["color"]

            if color == "yellow":
                yellow_counts[player_id] = yellow_counts.get(player_id, 0) + 1
                # A second raw "yellow" for the same player must never
                # happen — it should already have been converted to red.
                assert yellow_counts[player_id] <= 1
            elif yellow_counts.get(player_id) == 1:
                found_second_yellow_case = True

    assert found_second_yellow_case


def test_a_sent_off_or_injured_player_never_appears_again_in_that_match():
    home = build_team("home", "Home", overall=60)
    away = build_team("away", "Away", overall=60)
    simulator = MatchSimulator()

    checked_at_least_one = False

    for seed in range(N):
        events = simulator.simulate(home, away, seed=seed)
        removed_at = {}

        for i, event in enumerate(events):
            is_red = event.type == EventType.CARD and event.payload.get("color") == "red"
            if is_red or event.type == EventType.INJURY:
                removed_at[event.player_ids[0]] = i

        for player_id, index in removed_at.items():
            later_events = events[index + 1:]
            assert all(player_id not in e.player_ids for e in later_events)
            checked_at_least_one = True

    assert checked_at_least_one
