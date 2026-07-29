"""PhaseRatingCalculator: turns player attributes into phase ratings.

See engine/rating/CLAUDE.md §1 and §4. Never branches on phase identity —
everything phase-specific comes from the weight tables in tables.py, so
rebalancing or adding a phase/attribute never touches this class.
"""

from app.domain.player import Player
from app.engine.phase import Phase
from app.engine.rating.tables import (
    PHASE_ATTACK_WEIGHTS,
    PHASE_DEFENSE_WEIGHTS,
    eligible_players,
)


class PhaseRatingCalculator:
    """Team-aggregate rating for a phase, and single-player scoring against
    the same weight tables (used to blend in a protagonist's individual
    contribution — see engine/rating/CLAUDE.md §3)."""

    def rate(self, phase: Phase, players: list[Player], side: str) -> float:
        """Weighted average of the eligible players' attribute scores."""
        weights = self._weights(phase, side)
        eligible = eligible_players(phase, players, side)
        scores = [self._weighted_score(player, weights) for player in eligible]
        return sum(scores) / len(scores)

    def individual_score(self, phase: Phase, player: Player, side: str) -> float:
        return self._weighted_score(player, self._weights(phase, side))

    @staticmethod
    def _weights(phase: Phase, side: str) -> dict[str, float]:
        return PHASE_ATTACK_WEIGHTS[phase] if side == "attack" else PHASE_DEFENSE_WEIGHTS[phase]

    @staticmethod
    def _weighted_score(player: Player, weights: dict[str, float]) -> float:
        return sum(getattr(player.attributes, attribute) * weight for attribute, weight in weights.items())
