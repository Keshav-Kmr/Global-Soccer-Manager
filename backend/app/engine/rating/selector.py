"""ProtagonistSelector: weighted-random pick of the player 'on the ball' for
a phase, for narrative purposes and individual-attribute nuance.

See engine/rating/CLAUDE.md §2. Must always be given the match's shared
random.Random instance — never a fresh Random() — so the whole simulation
stays reproducible from a single seed.
"""

import random

from app.domain.player import Player
from app.engine.phase import Phase
from app.engine.rating.tables import INVOLVEMENT_WEIGHTS, eligible_players


class ProtagonistSelector:
    def select(self, phase: Phase, players: list[Player], side: str, rng: random.Random) -> Player:
        eligible = eligible_players(phase, players, side)
        weights_table = INVOLVEMENT_WEIGHTS[side]
        weights = [self._involvement(player, weights_table) for player in eligible]
        return rng.choices(eligible, weights=weights, k=1)[0]

    @staticmethod
    def _involvement(player: Player, weights: dict[str, float]) -> float:
        return sum(getattr(player.attributes, attribute) * weight for attribute, weight in weights.items())
