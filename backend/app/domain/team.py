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

        # Deliberately NOT snapshotted here: a caller commonly customizes
        # starting_xi/bench after construction (e.g. swapping in a hand-
        # built star player) before ever starting a Match, and snapshotting
        # this early would capture the pre-customization roster instead.
        # Match.__init__ takes this snapshot lazily on the *first* match it
        # simulates for this Team, and restores from it on every later one
        # — see Match.__init__ for why.
        self._original_starting_xi: list[Player] | None = None
        self._original_bench: list[Player] | None = None
