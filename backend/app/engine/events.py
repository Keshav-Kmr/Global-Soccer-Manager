"""MatchEvent: the engine's only output.

Delivery and commentary consume these; engine internals never format text
(see app/commentary/CLAUDE.md on why that's a separate layer). This is a
subset of the full taxonomy in engine/CLAUDE.md §10 — fouls, cards,
injuries, substitutions, and set-piece event types arrive with the
corresponding roadmap items, not in this first pass.
"""

from dataclasses import dataclass, field
from enum import Enum


class EventType(str, Enum):
    KICKOFF = "kickoff"
    POSSESSION_PROGRESS = "possession_progress"
    TURNOVER = "turnover"
    SHOT = "shot"
    GOAL = "goal"
    SAVE = "save"
    BLOCK = "block"
    OFF_TARGET = "off_target"
    FULL_TIME = "full_time"


@dataclass
class MatchEvent:
    minute: int
    type: EventType
    team_id: str | None
    player_ids: list[str] = field(default_factory=list)
    payload: dict = field(default_factory=dict)
