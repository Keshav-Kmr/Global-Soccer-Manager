"""ProbabilityModel: the single contest-resolution primitive every duel in
the engine goes through. See engine/CLAUDE.md §4.

SPREAD/P_MIN/P_MAX are tuning constants, not derived values. Current values
were calibrated empirically (see scripts/simulate_demo.py and the
statistical tests in tests/engine/test_match_simulator.py): a possession
chain requires winning several *sequential* contests (three progression
phases plus a shot — see possession_chain.py), so per-duel probabilities
compound multiplicatively over one chain. A SPREAD that looks reasonable
for a single duel can crush the underdog at the match level once you
chain four of them — an early version of this engine used SPREAD=20 with
P_MIN/P_MAX=0.10/0.90 and a 15-point attribute gap alone produced a 93%
win rate with the underdog winning under 1% of the time, defeating the
"variance is a real pillar" requirement in the root CLAUDE.md. These wider
values were chosen so that gap keeps mattering while upsets stay
plausible; treat them as a starting point to keep refining, not a final
answer. A single global SPREAD is a deliberate v1 simplification;
engine/CLAUDE.md notes it could become per-phase later without changing
this class's interface.
"""

import math
import random

SPREAD = 60.0
P_MIN = 0.20
P_MAX = 0.80


class ProbabilityModel:
    """Resolves one contest between an attacking and a defending rating."""

    def resolve(self, attacker_rating: float, defender_rating: float, rng: random.Random) -> bool:
        """Returns True if the attacker wins the contest.

        `rng` must be the match's shared random.Random instance so the
        whole simulation stays reproducible from a single seed.
        """
        raw_probability = 1 / (1 + math.exp(-(attacker_rating - defender_rating) / SPREAD))
        probability = min(max(raw_probability, P_MIN), P_MAX)
        return rng.random() < probability
