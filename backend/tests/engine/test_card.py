import random

from app.engine.card import Card, CardCheck


def test_higher_severity_increases_card_chance():
    rng_low = random.Random(0)
    rng_high = random.Random(0)
    check = CardCheck()

    low = sum(check.roll(0.0, 1.0, rng_low) != Card.NONE for _ in range(3000))
    high = sum(check.roll(1.5, 1.0, rng_high) != Card.NONE for _ in range(3000))

    assert high > low


def test_stricter_referee_increases_card_chance():
    rng_lenient = random.Random(0)
    rng_strict = random.Random(0)
    check = CardCheck()

    lenient = sum(check.roll(1.0, 0.7, rng_lenient) != Card.NONE for _ in range(3000))
    strict = sum(check.roll(1.0, 1.3, rng_strict) != Card.NONE for _ in range(3000))

    assert strict > lenient


def test_red_cards_are_rarer_than_yellow_at_moderate_severity():
    rng = random.Random(0)
    check = CardCheck()

    results = [check.roll(0.8, 1.0, rng) for _ in range(5000)]

    assert results.count(Card.RED) < results.count(Card.YELLOW)
