from app.domain.tactic import Tactic, Width
from app.engine.phase import Phase
from app.engine.tactical_matchup import TacticalMatchup


def test_wide_attack_boosts_final_third_but_not_midfield():
    matchup = TacticalMatchup()
    wide = Tactic(width=Width.WIDE)
    normal = Tactic(width=Width.NORMAL)

    wide_final_third, _ = matchup.modifiers(Phase.FINAL_THIRD, wide, normal)
    normal_final_third, _ = matchup.modifiers(Phase.FINAL_THIRD, normal, normal)
    wide_midfield, _ = matchup.modifiers(Phase.MIDFIELD, wide, normal)
    normal_midfield, _ = matchup.modifiers(Phase.MIDFIELD, normal, normal)

    assert wide_final_third > normal_final_third
    assert wide_midfield == normal_midfield


def test_narrow_attack_boosts_midfield_but_not_final_third():
    matchup = TacticalMatchup()
    narrow = Tactic(width=Width.NARROW)
    normal = Tactic(width=Width.NORMAL)

    narrow_midfield, _ = matchup.modifiers(Phase.MIDFIELD, narrow, normal)
    normal_midfield, _ = matchup.modifiers(Phase.MIDFIELD, normal, normal)
    narrow_final_third, _ = matchup.modifiers(Phase.FINAL_THIRD, narrow, normal)
    normal_final_third, _ = matchup.modifiers(Phase.FINAL_THIRD, normal, normal)

    assert narrow_midfield > normal_midfield
    assert narrow_final_third == normal_final_third


def test_width_bonus_applies_to_the_defending_side_too():
    """A team defending wide covers the flank better, not just teams
    attacking wide — width isn't a one-sided bonus."""
    matchup = TacticalMatchup()
    wide_defense = Tactic(width=Width.WIDE)
    normal_defense = Tactic(width=Width.NORMAL)
    attacker_tactic = Tactic()

    _, defender_mod_wide = matchup.modifiers(Phase.FINAL_THIRD, attacker_tactic, wide_defense)
    _, defender_mod_normal = matchup.modifiers(Phase.FINAL_THIRD, attacker_tactic, normal_defense)

    assert defender_mod_wide > defender_mod_normal
