"""Team domain model: a matchday squad plus its tactical setup."""

from dataclasses import dataclass, field

from app.domain.player import Player
from app.domain.tactic import Tactic


@dataclass
class Team:
    id: str
    name: str
    starting_xi: list[Player]
    tactic: Tactic = field(default_factory=Tactic)
    bench: list[Player] = field(default_factory=list)

    def __post_init__(self) -> None:
        if len(self.starting_xi) != 11:
            raise ValueError(f"starting_xi must have exactly 11 players, got {len(self.starting_xi)}")
