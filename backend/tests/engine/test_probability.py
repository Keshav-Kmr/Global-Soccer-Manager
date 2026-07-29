import random

from app.engine.probability import P_MAX, P_MIN, ProbabilityModel


def test_equal_ratings_are_a_coin_flip_around_fifty_percent():
    model = ProbabilityModel()
    rng = random.Random(0)

    outcomes = [model.resolve(50.0, 50.0, rng) for _ in range(2000)]
    win_rate = sum(outcomes) / len(outcomes)

    assert 0.45 < win_rate < 0.55


def test_large_gap_is_clamped_rather_than_certain():
    model = ProbabilityModel()
    rng = random.Random(0)

    outcomes = [model.resolve(99.0, 1.0, rng) for _ in range(2000)]
    win_rate = sum(outcomes) / len(outcomes)

    # Clamped to P_MAX, not 1.0 — the underdog must still win sometimes.
    assert abs(win_rate - P_MAX) < 0.03


def test_reverse_gap_is_clamped_at_the_floor():
    model = ProbabilityModel()
    rng = random.Random(0)

    outcomes = [model.resolve(1.0, 99.0, rng) for _ in range(2000)]
    win_rate = sum(outcomes) / len(outcomes)

    assert abs(win_rate - P_MIN) < 0.03


def test_same_seed_is_deterministic():
    model = ProbabilityModel()
    rng_a = random.Random(42)
    rng_b = random.Random(42)

    outcomes_a = [model.resolve(55.0, 45.0, rng_a) for _ in range(50)]
    outcomes_b = [model.resolve(55.0, 45.0, rng_b) for _ in range(50)]

    assert outcomes_a == outcomes_b
