"""FoulCheck: decides whether a lost progression duel was a clean tackle or
a foul, and if so, how severe it was. See engine/CLAUDE.md §6.

Only rolled when the attacker loses a progression phase (BUILD_UP,
MIDFIELD, FINAL_THIRD) — a phase the attacker *wins* is treated as clean
possession play, not a physical duel worth checking for a foul. SHOT is
excluded too (a foul that stops a shot is a penalty, a distinct future
mechanic — see engine/CLAUDE.md §7 on set pieces).
"""

import random

from app.domain.player import Player
from app.engine.phase import Phase

FOUL_CHANCE = 0.25

# Fouls that stop a promising, advanced attack read as more cynical/severe
# than a foul in a team's own defensive third.
_ZONE_SEVERITY = {Phase.BUILD_UP: 0.8, Phase.MIDFIELD: 1.0, Phase.FINAL_THIRD: 1.3}


class FoulOutcome:
    def __init__(self, is_foul: bool, severity: float = 0.0):
        self.is_foul = is_foul
        self.severity = severity


class FoulCheck:
    def roll(self, phase: Phase, tackler: Player, ball_carrier: Player, rng: random.Random) -> FoulOutcome:
        """`rng` must be the match's shared random.Random instance."""
        if rng.random() >= FOUL_CHANCE:
            return FoulOutcome(is_foul=False)

        # A reckless tackler up against a hard-to-dispossess dribbler makes
        # for a more severe foul; zone scales it further. Floor at 0 — a
        # cynical foul by a disciplined player on a weak dribbler is still
        # a foul, just a less severe one (CardCheck has its own floor).
        aggression_gap = tackler.attributes.aggression - ball_carrier.attributes.dribbling
        severity = max(0.0, (aggression_gap + 50) / 100) * _ZONE_SEVERITY[phase]
        return FoulOutcome(is_foul=True, severity=severity)
