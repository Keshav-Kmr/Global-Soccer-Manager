import random

from app.domain.player import Player, PlayerAttributes, Position
from app.engine.brilliance import BrillianceCheck


def _player_with_flair(flair: int) -> Player:
    attrs = dict(
        pace=1, dribbling=1, passing=1, vision=1, shooting=1, tackling=1,
        marking=1, strength=1, positioning=1, aggression=1, composure=1, stamina=1,
        flair=flair,
    )
    return Player(id="p", name="Test Player", position=Position.ST, attributes=PlayerAttributes(**attrs))


def test_low_flair_player_rarely_but_sometimes_produces_brilliance():
    player = _player_with_flair(1)
    rng = random.Random(0)
    check = BrillianceCheck()

    hits = sum(check.roll(player, rng) for _ in range(5000))
    rate = hits / 5000

    assert 0.0 < rate < 0.03


def test_high_flair_player_produces_brilliance_more_often_but_still_rarely():
    player = _player_with_flair(99)
    rng = random.Random(0)
    check = BrillianceCheck()

    hits = sum(check.roll(player, rng) for _ in range(5000))
    rate = hits / 5000

    # Meaningfully more likely than a low-flair player, but capped low —
    # if this stops being rare, it stops reading as a moment of brilliance.
    assert 0.04 < rate < 0.08


def test_flair_changes_the_rate_meaningfully():
    rng_low = random.Random(0)
    rng_high = random.Random(0)
    check = BrillianceCheck()

    low_rate = sum(check.roll(_player_with_flair(1), rng_low) for _ in range(5000)) / 5000
    high_rate = sum(check.roll(_player_with_flair(99), rng_high) for _ in range(5000)) / 5000

    assert high_rate > low_rate * 3
