"""Validated football formations: slot positions for the starting XI."""

from enum import Enum

from app.domain.player import Player, Position


class Formation(str, Enum):
    FOUR_THREE_THREE = "4-3-3"
    FOUR_TWO_THREE_ONE = "4-2-3-1"
    FOUR_FOUR_TWO = "4-4-2"
    THREE_FIVE_TWO = "3-5-2"
    THREE_FOUR_THREE = "3-4-3"
    FIVE_THREE_TWO = "5-3-2"


FORMATION_SLOTS: dict[Formation, list[Position]] = {
    Formation.FOUR_THREE_THREE: [
        Position.GK,
        Position.CB, Position.CB, Position.FB, Position.FB,
        Position.DM, Position.CM, Position.CM,
        Position.W, Position.ST, Position.W,
    ],
    Formation.FOUR_TWO_THREE_ONE: [
        Position.GK,
        Position.CB, Position.CB, Position.FB, Position.FB,
        Position.DM, Position.DM,
        Position.W, Position.AM, Position.W,
        Position.ST,
    ],
    Formation.FOUR_FOUR_TWO: [
        Position.GK,
        Position.CB, Position.CB, Position.FB, Position.FB,
        Position.CM, Position.CM, Position.W, Position.W,
        Position.ST, Position.ST,
    ],
    Formation.THREE_FIVE_TWO: [
        Position.GK,
        Position.CB, Position.CB, Position.CB,
        Position.FB, Position.DM, Position.CM, Position.CM, Position.FB,
        Position.ST, Position.ST,
    ],
    Formation.THREE_FOUR_THREE: [
        Position.GK,
        Position.CB, Position.CB, Position.CB,
        Position.CM, Position.CM, Position.W, Position.W,
        Position.AM, Position.ST, Position.W,
    ],
    Formation.FIVE_THREE_TWO: [
        Position.GK,
        Position.FB, Position.CB, Position.CB, Position.CB, Position.FB,
        Position.CM, Position.CM, Position.DM,
        Position.ST, Position.ST,
    ],
}

# Normalized pitch anchors (x length, y width) for each slot index — home attacks toward x=100.
FORMATION_ANCHORS: dict[Formation, list[tuple[float, float]]] = {
    Formation.FOUR_THREE_THREE: [
        (5, 50),
        (22, 38), (22, 62), (25, 18), (25, 82),
        (40, 50), (48, 35), (48, 65),
        (70, 15), (78, 50), (70, 85),
    ],
    Formation.FOUR_TWO_THREE_ONE: [
        (5, 50),
        (22, 38), (22, 62), (25, 18), (25, 82),
        (42, 40), (42, 60),
        (68, 18), (72, 50), (68, 82),
        (80, 50),
    ],
    Formation.FOUR_FOUR_TWO: [
        (5, 50),
        (22, 38), (22, 62), (25, 18), (25, 82),
        (50, 20), (50, 40), (50, 60), (50, 80),
        (75, 42), (75, 58),
    ],
    Formation.THREE_FIVE_TWO: [
        (5, 50),
        (20, 30), (22, 50), (20, 70),
        (45, 12), (48, 35), (50, 50), (48, 65), (45, 88),
        (76, 42), (76, 58),
    ],
    Formation.THREE_FOUR_THREE: [
        (5, 50),
        (20, 30), (22, 50), (20, 70),
        (48, 25), (48, 45), (48, 55), (48, 75),
        (72, 50), (78, 50), (70, 20),
    ],
    Formation.FIVE_THREE_TWO: [
        (5, 50),
        (24, 10), (22, 35), (22, 50), (22, 65), (24, 90),
        (50, 30), (50, 50), (50, 70),
        (76, 42), (76, 58),
    ],
}


def validate_starting_xi(starting_xi: list[Player], formation: Formation) -> None:
    """Raise ValueError if the lineup does not match the formation."""
    if len(starting_xi) != 11:
        raise ValueError(f"starting_xi must have exactly 11 players, got {len(starting_xi)}")

    slots = FORMATION_SLOTS[formation]
    if len(slots) != 11:
        raise ValueError(f"formation {formation.value} is invalid")

    for index, (player, expected) in enumerate(zip(starting_xi, slots, strict=True)):
        if player.position != expected:
            raise ValueError(
                f"slot {index}: expected {expected.value}, got {player.position.value} "
                f"for formation {formation.value}"
            )