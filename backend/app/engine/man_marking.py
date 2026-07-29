"""ManMarking: the defending team's marking_scheme trade-off. See
engine/CLAUDE.md §2.

Man-to-man marking is meant to neutralize a genuinely standout attacking
protagonist at the cost of weakening general coverage otherwise — a real
trade-off, not a free counter. That means it needs to know how good the
specific attacker is *this contest* (their individual phase rating), which
TacticalMatchup deliberately never sees (it's a pure function of tactics +
phase, no player data) — hence this being its own small class rather than
a branch inside that one.
"""

from app.domain.tactic import MarkingScheme, Tactic
from app.engine.phase import Phase

COVERAGE_PENALTY = 0.95
STAR_NULLIFICATION_BONUS = 1.25
STAR_THRESHOLD = 75.0


class ManMarking:
    def defender_modifier(self, defending_tactic: Tactic, attacker_individual_rating: float, phase: Phase) -> float:
        """A flat penalty for the marker being tied to their man instead
        of covering their zone, offset by a bonus that only kicks in
        against a genuine standout (attacker_individual_rating clearing
        STAR_THRESHOLD) — so man-marking is a net loss against an ordinary
        player and a net gain against a real one.

        Never applies to Phase.SHOT: a goalkeeper facing a shot isn't "man
        marking" anyone in the sense this models — that's open-play
        defending against a specific playmaker/dribbler."""
        if phase == Phase.SHOT or defending_tactic.marking_scheme != MarkingScheme.MAN_TO_MAN:
            return 1.0

        modifier = COVERAGE_PENALTY
        if attacker_individual_rating >= STAR_THRESHOLD:
            modifier *= STAR_NULLIFICATION_BONUS
        return modifier
