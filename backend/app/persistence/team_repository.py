"""TeamRepository: the interface MatchService/routes depend on for
persisting rosters — never a concrete SQL/ORM class directly (backend/CLAUDE.md).
"""

from abc import ABC, abstractmethod

from app.domain.team import Team


class TeamRepository(ABC):
    @abstractmethod
    async def save(self, team: Team) -> None:
        """Creates or fully replaces the team with this id (upsert)."""

    @abstractmethod
    async def get(self, team_id: str) -> Team | None:
        ...

    @abstractmethod
    async def list_all(self) -> list[Team]:
        ...
