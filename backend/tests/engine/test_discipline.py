"""Statistical tests proving fouls/cards/injuries actually fire during a
full match and have the right consequences — not just that the isolated
check classes work in unit tests. See backend/CLAUDE.md testing philosophy.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from factories import build_team

from app.engine.auto_substitution import MAX_SUBSTITUTIONS
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
    """A red card always ends a player's match; an injury usually does too
    unless AutoSubstitution brings on a replacement (engine/CLAUDE.md §8),
    in which case the SUBSTITUTION event legitimately names them one more
    time as the player going off — that's the one exception checked for."""
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
            later_events = [e for e in events[index + 1:] if e.type != EventType.SUBSTITUTION]
            assert all(player_id not in e.player_ids for e in later_events)
            checked_at_least_one = True

    assert checked_at_least_one


def test_both_injury_and_tiredness_triggered_substitutions_occur():
    home = build_team("home", "Home", overall=60)
    away = build_team("away", "Away", overall=60)
    simulator = MatchSimulator()

    reasons: dict[str, int] = {}
    for seed in range(N):
        events = simulator.simulate(home, away, seed=seed)
        for sub_event in _of_type(events, EventType.SUBSTITUTION):
            reason = sub_event.payload["reason"]
            reasons[reason] = reasons.get(reason, 0) + 1

    assert reasons.get("injury", 0) > 0
    assert reasons.get("tiredness", 0) > 0


def test_a_red_card_never_triggers_an_automatic_substitution():
    """Real football doesn't let you replace a sent-off player — nothing
    in AutoSubstitution reacts to a CARD event, only INJURY (and fatigue,
    unrelated to cards), so a red-carded player must never show up as the
    outgoing player of any later substitution."""
    home = build_team("home", "Home", overall=60)
    away = build_team("away", "Away", overall=60)
    simulator = MatchSimulator()

    found_a_red_card = False

    for seed in range(N):
        events = simulator.simulate(home, away, seed=seed)
        for i, event in enumerate(events):
            if event.type != EventType.CARD or event.payload.get("color") != "red":
                continue
            found_a_red_card = True
            sent_off_player = event.player_ids[0]
            later_subs = _of_type(events[i + 1 :], EventType.SUBSTITUTION)
            assert all(sub.player_ids[0] != sent_off_player for sub in later_subs)

    assert found_a_red_card


def test_substitution_limit_is_never_exceeded():
    home = build_team("home", "Home", overall=60)
    away = build_team("away", "Away", overall=60)
    simulator = MatchSimulator()

    for seed in range(N):
        events = simulator.simulate(home, away, seed=seed)
        for team_id in (home.id, away.id):
            auto_subs = [
                e for e in _of_type(events, EventType.SUBSTITUTION)
                if e.team_id == team_id and e.payload.get("reason") in ("injury", "tiredness")
            ]
            assert len(auto_subs) <= MAX_SUBSTITUTIONS
