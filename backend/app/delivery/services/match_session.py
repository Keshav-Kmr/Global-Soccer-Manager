"""In-process state for a live match session (auto or controlled)."""

from dataclasses import dataclass, field
from enum import Enum
import random

from app.domain.player import Player
from app.domain.team import Team
from app.engine.match import Match


class MatchRunMode(str, Enum):
    AUTO = "auto"
    CONTROLLED = "controlled"


@dataclass
class MatchSession:
    match_id: str
    match: Match
    team_a: Team
    team_b: Team
    roster: dict[str, Player]
    commentary_rng: random.Random
    mode: MatchRunMode
    wired_event_count: int = 0
    wire_log: list[dict] = field(default_factory=list)