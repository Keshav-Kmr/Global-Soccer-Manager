"""MatchEvent: the engine's only output.

Delivery and commentary consume these; engine internals never format text
(see app/commentary/CLAUDE.md on why that's a separate layer). This is a
subset of the full taxonomy in engine/CLAUDE.md §10 — offside, set pieces,
and half-time arrive with the corresponding roadmap items, not in this
first pass.
"""

from dataclasses import dataclass, field
from enum import Enum


class EventType(str, Enum):
    KICKOFF = "kickoff"
    POSSESSION_PROGRESS = "possession_progress"
    TURNOVER = "turnover"
    MOMENT_OF_BRILLIANCE = "moment_of_brilliance"
    FOUL = "foul"
    CARD = "card"
    INJURY = "injury"
    SHOT = "shot"
    GOAL = "goal"
    SAVE = "save"
    BLOCK = "block"
    OFF_TARGET = "off_target"
    TACTIC_CHANGE = "tactic_change"
    FORMATION_CHANGE = "formation_change"
    SUBSTITUTION = "substitution"
    HALF_TIME = "half_time"
    FULL_TIME = "full_time"
    OFFSIDE = "offside"
    FREE_KICK = "free_kick"
    GOAL_KICK = "goal_kick"
    CORNER_KICK = "corner_kick"
    THROW_IN = "throw_in"
    PENALTY_AWARDED = "penalty_awarded"
    PENALTY_GOAL = "penalty_goal"
    PENALTY_SAVE = "penalty_save"
    PENALTY_MISS = "penalty_miss"


KEY_EVENT_TYPES = frozenset({
    EventType.GOAL,
    EventType.PENALTY_AWARDED,
    EventType.PENALTY_GOAL,
    EventType.CARD,
    EventType.INJURY,
    EventType.SUBSTITUTION,
    EventType.HALF_TIME,
})


_STOPPAGE_EVENT_TYPES = frozenset({
    EventType.GOAL,
    EventType.PENALTY_GOAL,
    EventType.FOUL,
    EventType.CARD,
    EventType.INJURY,
    EventType.SUBSTITUTION,
    EventType.TACTIC_CHANGE,
    EventType.PENALTY_AWARDED,
    EventType.GOAL_KICK,
    EventType.CORNER_KICK,
    EventType.THROW_IN,
})


@dataclass
class MatchEvent:
    minute: int
    type: EventType
    team_id: str | None
    player_ids: list[str] = field(default_factory=list)
    payload: dict = field(default_factory=dict)
