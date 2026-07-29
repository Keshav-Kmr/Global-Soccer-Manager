import random

from app.domain.player import Player, PlayerAttributes, Position
from app.engine.foul import FOUL_CHANCE, FoulCheck
from app.engine.phase import Phase


def _player(aggression=50, dribbling=50) -> Player:
    attrs = dict(
        pace=1, dribbling=dribbling, passing=1, vision=1, shooting=1, tackling=1,
        marking=1, strength=1, positioning=1, aggression=aggression, composure=1, stamina=1, flair=1,
    )
    return Player(id="p", name="Test Player", position=Position.CB, attributes=PlayerAttributes(**attrs))


def _average_severity(check: FoulCheck, phase: Phase, tackler: Player, carrier: Player, rng: random.Random) -> float:
    outcomes = [check.roll(phase, tackler, carrier, rng) for _ in range(3000)]
    severities = [o.severity for o in outcomes if o.is_foul]
    return sum(severities) / len(severities)


def test_foul_rate_matches_the_foul_chance_constant():
    rng = random.Random(0)
    check = FoulCheck()
    tackler, carrier = _player(), _player()

    outcomes = [check.roll(Phase.MIDFIELD, tackler, carrier, rng) for _ in range(5000)]
    rate = sum(o.is_foul for o in outcomes) / 5000

    assert abs(rate - FOUL_CHANCE) < 0.03


def test_bigger_aggression_vs_dribbling_gap_is_more_severe():
    rng = random.Random(1)
    check = FoulCheck()

    reckless_tackler, weak_dribbler = _player(aggression=90), _player(dribbling=20)
    mild_tackler, strong_dribbler = _player(aggression=20), _player(dribbling=90)

    high_gap = _average_severity(check, Phase.MIDFIELD, reckless_tackler, weak_dribbler, rng)
    low_gap = _average_severity(check, Phase.MIDFIELD, mild_tackler, strong_dribbler, rng)

    assert high_gap > low_gap


def test_final_third_fouls_are_more_severe_than_build_up_fouls():
    rng = random.Random(2)
    check = FoulCheck()
    tackler, carrier = _player(aggression=60), _player(dribbling=60)

    final_third = _average_severity(check, Phase.FINAL_THIRD, tackler, carrier, rng)
    build_up = _average_severity(check, Phase.BUILD_UP, tackler, carrier, rng)

    assert final_third > build_up
