import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from factories import build_team

from app.domain.player import Position
from app.engine.auto_substitution import MAX_SUBSTITUTIONS, TIREDNESS_FITNESS_THRESHOLD, AutoSubstitution


def test_injury_brings_on_a_like_for_like_bench_player():
    team = build_team("home", "Home", overall=60)
    injured = team.starting_xi[9]  # ST slot
    assert injured.position == Position.ST

    event = AutoSubstitution().substitute_for_injury(team, minute=30, injured_player=injured)

    assert event is not None
    assert event.payload == {"reason": "injury"}
    assert event.player_ids[0] == injured.id
    replacement_id = event.player_ids[1]
    assert team.starting_xi[9].id == replacement_id
    assert not any(p.id == replacement_id for p in team.bench)


def test_no_replacement_available_returns_none():
    team = build_team("home", "Home", overall=60)
    team.bench = [p for p in team.bench if p.position != Position.ST]  # remove the only ST cover
    injured = team.starting_xi[9]

    event = AutoSubstitution().substitute_for_injury(team, minute=30, injured_player=injured)

    assert event is None
    assert team.starting_xi[9] is injured


def test_substitution_limit_is_enforced():
    team = build_team("home", "Home", overall=60)
    team.substitutions_used = MAX_SUBSTITUTIONS
    injured = team.starting_xi[9]

    event = AutoSubstitution().substitute_for_injury(team, minute=30, injured_player=injured)

    assert event is None
    assert team.starting_xi[9] is injured


def test_tiredness_substitutes_the_single_most_tired_eligible_starter():
    team = build_team("home", "Home", overall=60)
    team.starting_xi[9].fitness = TIREDNESS_FITNESS_THRESHOLD - 0.2  # ST, most tired
    team.starting_xi[6].fitness = TIREDNESS_FITNESS_THRESHOLD - 0.05  # CM, tired but less so

    event = AutoSubstitution().substitute_for_tiredness(team, minute=70)

    assert event is not None
    assert event.payload == {"reason": "tiredness"}
    assert event.player_ids[0] == "home_9"


def test_no_tiredness_substitution_when_nobody_is_tired_enough():
    team = build_team("home", "Home", overall=60)

    event = AutoSubstitution().substitute_for_tiredness(team, minute=70)

    assert event is None


def test_an_unavailable_starter_is_never_substituted_for_tiredness():
    team = build_team("home", "Home", overall=60)
    tired_but_gone = team.starting_xi[9]
    tired_but_gone.fitness = 0.1
    tired_but_gone.available = False  # already sent off/injured

    event = AutoSubstitution().substitute_for_tiredness(team, minute=70)

    assert event is None


def test_bench_player_already_used_elsewhere_is_not_picked_again():
    team = build_team("home", "Home", overall=60)
    for player in team.bench:
        if player.position == Position.ST:
            player.available = False  # already subbed on and off again, hypothetically

    injured = team.starting_xi[9]
    event = AutoSubstitution().substitute_for_injury(team, minute=30, injured_player=injured)

    assert event is None
