"""TacticalMatchup: asymmetric modifiers from comparing both teams' tactics,
applied before a phase contest runs. See engine/CLAUDE.md §2.

This is what makes tactics a structural pillar rather than a flat
coefficient — a pure function of both teams' dials and the current phase,
no player data, no randomness.

v1 wires up mentality, pressing, and defensive line, matching the examples
in engine/CLAUDE.md §2. `width` and `marking_scheme` are deliberately left
unwired for now (see domain/tactic.py) rather than half-implemented —
they're tracked as remaining Phase 1 work, not silently ignored.
"""

from app.domain.tactic import DefensiveLine, Mentality, Pressing, Tactic
from app.engine.phase import Phase

_MENTALITY_ATTACK_MOD = {
    Mentality.DEFENSIVE: 0.90,
    Mentality.BALANCED: 1.00,
    Mentality.ATTACKING: 1.15,
}
_MENTALITY_DEFENSE_MOD = {
    Mentality.DEFENSIVE: 1.15,
    Mentality.BALANCED: 1.00,
    Mentality.ATTACKING: 0.85,
}
_PRESSING_BUILDUP_PENALTY = {
    Pressing.LOW: 1.00,
    Pressing.MEDIUM: 0.95,
    Pressing.HIGH: 0.85,
}
_HIGH_LINE_FINAL_THIRD_BONUS = 1.15

_PROGRESSION_PHASES = (Phase.BUILD_UP, Phase.MIDFIELD)


class TacticalMatchup:
    def modifiers(
        self, phase: Phase, attacking_tactic: Tactic, defending_tactic: Tactic
    ) -> tuple[float, float]:
        """Returns (attacker_modifier, defender_modifier) for this phase."""
        attacker_mod = _MENTALITY_ATTACK_MOD[attacking_tactic.mentality]
        defender_mod = _MENTALITY_DEFENSE_MOD[defending_tactic.mentality]

        if phase in _PROGRESSION_PHASES:
            attacker_mod *= _PRESSING_BUILDUP_PENALTY[defending_tactic.pressing]

        if phase == Phase.FINAL_THIRD and defending_tactic.defensive_line == DefensiveLine.HIGH:
            attacker_mod *= _HIGH_LINE_FINAL_THIRD_BONUS

        return attacker_mod, defender_mod
