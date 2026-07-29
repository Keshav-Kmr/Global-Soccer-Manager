"""InjuryCheck: a small, independent chance of injury on a contested duel —
higher when it was a foul, but never zero on a hard clean tackle either.
See engine/CLAUDE.md §6.

Deliberately not derived from card severity: a perfectly legal, hard-fought
tackle can still injure someone, and most fouls don't. Two separate risks,
checked on two separate players by possession_chain.py: a foul's victim
(the ball carrier who got fouled) and a clean tackle's initiator (the
tackler risking themselves in a strong but fair challenge).
"""

import random

from app.domain.player import Player

CLEAN_TACKLE_BASE_CHANCE = 0.003
FOUL_BASE_CHANCE = 0.02
AGGRESSION_SCALE = 0.02


class InjuryCheck:
    def roll(self, player_at_risk: Player, rng: random.Random, was_foul: bool) -> bool:
        """`rng` must be the match's shared random.Random instance."""
        base = FOUL_BASE_CHANCE if was_foul else CLEAN_TACKLE_BASE_CHANCE
        chance = base + AGGRESSION_SCALE * (player_at_risk.attributes.aggression / 99)
        return rng.random() < chance
