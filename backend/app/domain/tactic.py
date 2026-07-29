"""Tactical dials.

See engine/CLAUDE.md §1 for what each dial is meant to affect mechanically,
and engine/tactical_matchup.py for which of these are actually wired into
the simulation so far — `width` and `marking_scheme` are modeled here as
data (so they can be selected and saved) but are not yet mechanically
active; see the TODO note in tactical_matchup.py.
"""

from dataclasses import dataclass
from enum import Enum


class Mentality(str, Enum):
    DEFENSIVE = "defensive"
    BALANCED = "balanced"
    ATTACKING = "attacking"


class Tempo(str, Enum):
    SLOW = "slow"
    NORMAL = "normal"
    FAST = "fast"


class Pressing(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Width(str, Enum):
    NARROW = "narrow"
    NORMAL = "normal"
    WIDE = "wide"


class DefensiveLine(str, Enum):
    DEEP = "deep"
    NORMAL = "normal"
    HIGH = "high"


class MarkingScheme(str, Enum):
    ZONAL = "zonal"
    MAN_TO_MAN = "man_to_man"


@dataclass(frozen=True)
class Tactic:
    mentality: Mentality = Mentality.BALANCED
    tempo: Tempo = Tempo.NORMAL
    pressing: Pressing = Pressing.MEDIUM
    width: Width = Width.NORMAL
    defensive_line: DefensiveLine = DefensiveLine.NORMAL
    marking_scheme: MarkingScheme = MarkingScheme.ZONAL
