"""TacticalMatchup: asymmetric modifiers from comparing both teams' tactics,
applied before a phase contest runs. See engine/CLAUDE.md §2.

This is what makes tactics a structural pillar rather than a flat
coefficient — a pure function of both teams' dials and the current phase,
no player data, no randomness.

v1 wires up mentality, pressing, defensive line, and width, matching the
examples in engine/CLAUDE.md §2. `marking_scheme` is deliberately handled
elsewhere (engine/man_marking.py): it needs to know how good the specific
attacking protagonist is this contest, which would break this class's
"no player data" contract — see that module's docstring.
"""

from app.domain.tactic import DefensiveLine, Mentality, Pressing, Tactic, Width
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

# A wide setup leans on wingers/fullbacks, who thrive in the FINAL_THIRD
# phase; a narrow setup overloads the center, who thrive in MIDFIELD.
# Applied to whichever side (attack or defense) actually plays that way —
# a team defending wide still covers the flank better, not just teams
# attacking wide.
_WIDE_FINAL_THIRD_BONUS = 1.10
_NARROW_MIDFIELD_BONUS = 1.10

_PROGRESSION_PHASES = (Phase.BUILD_UP, Phase.MIDFIELD)


def _width_modifier(tactic: Tactic, phase: Phase) -> float:
    if tactic.width == Width.WIDE and phase == Phase.FINAL_THIRD:
        return _WIDE_FINAL_THIRD_BONUS
    if tactic.width == Width.NARROW and phase == Phase.MIDFIELD:
        return _NARROW_MIDFIELD_BONUS
    return 1.0


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

        attacker_mod *= _width_modifier(attacking_tactic, phase)
        defender_mod *= _width_modifier(defending_tactic, phase)

        return attacker_mod, defender_mod
