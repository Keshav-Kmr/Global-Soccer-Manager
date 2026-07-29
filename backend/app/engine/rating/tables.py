"""Data tables driving the rating layer. See engine/rating/CLAUDE.md §4:
rebalancing or extending the engine should mean editing these tables, not
branching logic in PhaseRatingCalculator or ProtagonistSelector.

All weight dicts for a given (phase, side) sum to 1.0 by convention, so a
`rate()`/`individual_score()` result stays on roughly the same 1-99 scale
as the raw attributes being averaged.
"""

from app.domain.player import Player, Position
from app.engine.phase import Phase

# Which position codes are eligible to be the protagonist/contributor on
# each side of each phase's contest.
PHASE_ELIGIBLE_POSITIONS: dict[Phase, dict[str, list[Position]]] = {
    Phase.BUILD_UP: {
        "attack": [Position.GK, Position.CB, Position.DM],
        "defense": [Position.ST, Position.AM, Position.W],
    },
    Phase.MIDFIELD: {
        "attack": [Position.DM, Position.CM, Position.AM],
        "defense": [Position.CM, Position.DM],
    },
    Phase.FINAL_THIRD: {
        "attack": [Position.AM, Position.W, Position.ST],
        "defense": [Position.CB, Position.FB],
    },
    Phase.SHOT: {
        "attack": [Position.ST, Position.AM, Position.W],
        "defense": [Position.GK],
    },
}

PHASE_ATTACK_WEIGHTS: dict[Phase, dict[str, float]] = {
    Phase.BUILD_UP: {"passing": 0.5, "composure": 0.2, "positioning": 0.3},
    Phase.MIDFIELD: {"passing": 0.4, "vision": 0.3, "dribbling": 0.3},
    Phase.FINAL_THIRD: {"dribbling": 0.4, "vision": 0.35, "pace": 0.25},
    Phase.SHOT: {"shooting": 0.7, "composure": 0.3},
}

PHASE_DEFENSE_WEIGHTS: dict[Phase, dict[str, float]] = {
    Phase.BUILD_UP: {"tackling": 0.4, "marking": 0.3, "positioning": 0.3},
    Phase.MIDFIELD: {"tackling": 0.5, "positioning": 0.3, "strength": 0.2},
    Phase.FINAL_THIRD: {"marking": 0.5, "positioning": 0.3, "tackling": 0.2},
    Phase.SHOT: {"reflexes": 0.6, "handling": 0.2, "gk_positioning": 0.2},
}

# Which attributes make a player want/get the ball for narrative-protagonist
# selection — a different concern from "how good are they at the phase"
# (that's PHASE_ATTACK_WEIGHTS/PHASE_DEFENSE_WEIGHTS above).
INVOLVEMENT_WEIGHTS: dict[str, dict[str, float]] = {
    "attack": {"vision": 0.5, "positioning": 0.5},
    "defense": {"positioning": 0.5, "aggression": 0.5},
}

# Team-aggregate vs. individual-protagonist blend used when building the
# effective rating for a contest. See engine/rating/CLAUDE.md §3.
BLEND = 0.7


def eligible_players(phase: Phase, players: list[Player], side: str) -> list[Player]:
    """Players occupying a position eligible for this phase/side, falling
    back to the whole squad if an unusual formation has no specialist on
    the pitch for it."""
    positions = PHASE_ELIGIBLE_POSITIONS[phase][side]
    matched = [p for p in players if p.position in positions]
    return matched or players
