"""BrillianceCheck: a rare, independent chance for a player to produce a
standout individual moment — a moment of brilliance — that briefly lifts
their contribution to a single contest well above their usual level.

This is deliberately separate from PhaseRatingCalculator's team/individual
blend (engine/rating/CLAUDE.md §3), which is a smooth, continuous
statistical tilt. Brilliance is the opposite: a rare, discrete spike. This
is exactly the kind of thing engine/rating/CLAUDE.md §5 flagged as a future
extension point, and it plugs in without touching PhaseRatingCalculator,
ProbabilityModel, or the phase state machine at all — only
possession_chain.py's effective-rating computation needed to change.

MIN_CHANCE/MAX_CHANCE/BONUS_MULTIPLIER are tuning constants. It must stay
rare — if it fires often, it stops reading as a moment of brilliance and
just becomes noise.
"""

import random

from app.domain.player import Player

MIN_CHANCE = 0.01
MAX_CHANCE = 0.06
BONUS_MULTIPLIER = 1.8


class BrillianceCheck:
    def roll(self, player: Player, rng: random.Random) -> bool:
        """Returns True if this player produces a moment of brilliance in
        the contest currently being resolved. `rng` must be the match's
        shared random.Random instance."""
        chance = MIN_CHANCE + (player.attributes.flair / 99) * (MAX_CHANCE - MIN_CHANCE)
        return rng.random() < chance
