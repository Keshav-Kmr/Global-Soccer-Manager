"""TeamService: the only thing routes talk to for team persistence — see
backend/CLAUDE.md's routes -> services -> persistence rule. Thin on
purpose: there's no orchestration logic yet beyond the repository call
itself, but routes still go through this rather than a repository
directly, so that changes when there next non-trivial (defaults, an
optional AI-generated fallback, validation) don't move the layer boundary.
"""

from app.domain.team import Team
from app.persistence.team_repository import TeamRepository


class TeamService:
    def __init__(self, repository: TeamRepository) -> None:
        self._repository = repository

    async def save(self, team: Team) -> None:
        await self._repository.save(team)

    async def get(self, team_id: str) -> Team | None:
        return await self._repository.get(team_id)

    async def list_all(self) -> list[Team]:
        return await self._repository.list_all()
