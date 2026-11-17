"""MatchResultRepository: the durable record of a *finished* match — score,
participants, and the full (commentary-annotated) event log. Distinct from
the in-memory MatchRepository (in_memory_repository.py), which holds the
*live*, in-progress event log used for WebSocket streaming and is never
written to disk (see persistence/CLAUDE.md).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class MatchResult:
    match_id: str
    team_a_id: str
    team_a_name: str
    team_b_id: str
    team_b_name: str
    score_a: int
    score_b: int
    seed: int
    events: list[dict]
    statistics: dict | None = None
    summary: list[str] | None = None
    player_states: list[dict] | None = None


class MatchResultRepository(ABC):
    @abstractmethod
    async def save(self, result: MatchResult) -> None:
        ...

    @abstractmethod
    async def get(self, match_id: str) -> MatchResult | None:
        ...
