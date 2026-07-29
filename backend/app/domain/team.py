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
    # Match-day counter for automatic substitutions (engine/auto_substitution.py,
    # engine/CLAUDE.md §8) — reset to 0 at the start of every Match, alongside
    # the Player match-day fields (fitness, yellow_cards, available).
    substitutions_used: int = 0

    def __post_init__(self) -> None:
        if len(self.starting_xi) != 11:
            raise ValueError(f"starting_xi must have exactly 11 players, got {len(self.starting_xi)}")

        # Match() restores starting_xi/bench from these at the start of
        # every match, so substitutions made during one Match (manual or
        # automatic) never leak into a second, independent Match() call
        # that happens to reuse the same Team object — the same reason
        # Player.fitness/available get reset, applied to squad composition.
        self._original_starting_xi = list(self.starting_xi)
        self._original_bench = list(self.bench)
