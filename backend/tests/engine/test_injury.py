import random

from app.domain.player import Player, PlayerAttributes, Position
from app.engine.injury import InjuryCheck


def _player(aggression: int) -> Player:
    attrs = dict(
        pace=1, dribbling=1, passing=1, vision=1, shooting=1, tackling=1,
        marking=1, strength=1, positioning=1, aggression=aggression, composure=1, stamina=1, flair=1,
    )
    return Player(id="p", name="Test Player", position=Position.CB, attributes=PlayerAttributes(**attrs))


def test_a_foul_is_riskier_than_a_clean_tackle():
    rng_foul = random.Random(0)
    rng_clean = random.Random(0)
    check = InjuryCheck()
    player = _player(aggression=50)

    foul_injuries = sum(check.roll(player, rng_foul, was_foul=True) for _ in range(20000))
    clean_injuries = sum(check.roll(player, rng_clean, was_foul=False) for _ in range(20000))

    assert foul_injuries > clean_injuries


def test_injury_chance_stays_rare_even_for_a_maximally_aggressive_player():
    rng = random.Random(0)
    check = InjuryCheck()
    player = _player(aggression=99)

    injuries = sum(check.roll(player, rng, was_foul=True) for _ in range(5000))

    assert injuries / 5000 < 0.10
