"""Phase: the possession-chain state machine's phase identifiers.

See engine/CLAUDE.md §5 for the full state diagram. Only the progression
phases plus SHOT exist so far — set pieces, fouls/cards, and injuries are
tracked as separate, not-yet-implemented items on the Phase 1 roadmap.
"""

from enum import Enum


class Phase(str, Enum):
    BUILD_UP = "build_up"
    MIDFIELD = "midfield"
    FINAL_THIRD = "final_third"
    SHOT = "shot"
