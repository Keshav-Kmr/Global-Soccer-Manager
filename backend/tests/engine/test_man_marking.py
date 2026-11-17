import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from factories import build_team, make_player

from app.domain.player import Position
from app.domain.tactic import MarkingScheme, Tactic
from app.engine.man_marking import COVERAGE_PENALTY, STAR_THRESHOLD, ManMarking
from app.engine.phase import Phase


def test_zonal_marking_is_never_modified():
    marking = ManMarking()
    zonal = Tactic(marking_scheme=MarkingScheme.ZONAL)

    assert marking.defender_modifier(zonal, attacker_individual_rating=99.0, phase=Phase.MIDFIELD) == 1.0
    assert marking.defender_modifier(zonal, attacker_individual_rating=1.0, phase=Phase.MIDFIELD) == 1.0


def test_man_marking_hurts_against_an_ordinary_attacker():
    marking = ManMarking()
    man_to_man = Tactic(marking_scheme=MarkingScheme.MAN_TO_MAN)

    modifier = marking.defender_modifier(man_to_man, STAR_THRESHOLD - 20, phase=Phase.FINAL_THIRD)

    assert modifier == COVERAGE_PENALTY
    assert modifier < 1.0


def test_man_marking_helps_against_a_genuine_star():
    marking = ManMarking()
    man_to_man = Tactic(marking_scheme=MarkingScheme.MAN_TO_MAN)

    modifier = marking.defender_modifier(man_to_man, STAR_THRESHOLD + 20, phase=Phase.FINAL_THIRD)

    assert modifier > 1.0


def test_man_marking_is_a_real_tradeoff_not_a_free_bonus():
    """The bonus against a star must not simply cancel the coverage
    penalty for anyone below the threshold — there has to be a real cost
    for marking a player who doesn't turn out to be a threat."""
    marking = ManMarking()
    man_to_man = Tactic(marking_scheme=MarkingScheme.MAN_TO_MAN)
    zonal = Tactic(marking_scheme=MarkingScheme.ZONAL)

    ordinary_attacker_rating = STAR_THRESHOLD - 1
    man_marking_mod = marking.defender_modifier(man_to_man, ordinary_attacker_rating, phase=Phase.FINAL_THIRD)
    zonal_mod = marking.defender_modifier(zonal, ordinary_attacker_rating, phase=Phase.FINAL_THIRD)

    assert man_marking_mod < zonal_mod


def test_never_applies_to_the_shot_phase():
    """A goalkeeper facing a shot isn't 'man marking' the shooter — this
    mechanic is about open-play defending against a specific playmaker."""
    marking = ManMarking()
    man_to_man = Tactic(marking_scheme=MarkingScheme.MAN_TO_MAN)

    assert marking.defender_modifier(man_to_man, 99.0, phase=Phase.SHOT) == 1.0


