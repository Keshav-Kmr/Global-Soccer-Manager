"""Player domain model.

Pure data, no simulation logic — see backend/CLAUDE.md on why `domain/`
stays free of anything from `engine/` or `delivery/`.
"""

from dataclasses import dataclass
from enum import Enum

_ATTRIBUTE_MIN = 1
_ATTRIBUTE_MAX = 99


class Position(str, Enum):
    """Position codes. Drive phase eligibility — see engine/rating/CLAUDE.md."""

    GK = "GK"
    CB = "CB"
    FB = "FB"
    DM = "DM"
    CM = "CM"
    AM = "AM"
    W = "W"
    ST = "ST"


@dataclass(frozen=True)
class PlayerAttributes:
    """Attributes on a 1-99 scale. See engine/CLAUDE.md §1 for what each affects.

    The three goalkeeper-specific attributes default to the floor value and
    are simply never read for outfield players (only a GK is ever eligible
    on the defending side of a SHOT phase — see PHASE_ELIGIBLE_POSITIONS).

    `flair` drives BrillianceCheck (engine/brilliance.py): a rare, discrete
    chance of a standout individual moment, deliberately separate from the
    smooth team/individual blend in PhaseRatingCalculator — see
    engine/rating/CLAUDE.md §5.
    """

    pace: int
    dribbling: int
    passing: int
    vision: int
    shooting: int
    tackling: int
    marking: int
    strength: int
    positioning: int
    aggression: int
    composure: int
    stamina: int
    flair: int
    reflexes: int = _ATTRIBUTE_MIN
    handling: int = _ATTRIBUTE_MIN
    gk_positioning: int = _ATTRIBUTE_MIN

    def __post_init__(self) -> None:
        for field_name, value in self.__dict__.items():
            if not _ATTRIBUTE_MIN <= value <= _ATTRIBUTE_MAX:
                raise ValueError(
                    f"{field_name} must be between {_ATTRIBUTE_MIN} and "
                    f"{_ATTRIBUTE_MAX}, got {value}"
                )


@dataclass
class Player:
    """A single player. `fitness` is match-day state (depleted by
    FatigueModel as the match progresses); everything else is identity."""

    id: str
    name: str
    position: Position
    attributes: PlayerAttributes
    fitness: float = 1.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.fitness <= 1.0:
            raise ValueError(f"fitness must be between 0.0 and 1.0, got {self.fitness}")
