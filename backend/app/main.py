"""FastAPI application factory.

Run locally (from backend/, with the venv active):
    uvicorn app.main:app --reload

`MatchService`/`TeamService` and their repositories are constructed once
here and stashed on `app.state` — this is the single source of truth for
`Depends(get_match_service)`/`Depends(get_team_service)`
(delivery/api/matches.py, delivery/api/teams.py), so every viewer of a
given match shares the same running simulation, and every request sees
the same database.

`database_url` is a parameter, not a hardcoded global, so tests can point
`create_app()` at an isolated in-memory SQLite database — see
persistence/CLAUDE.md and persistence/database.py's module docstring on
why that matters (the same class of cross-run state leak this project has
hit more than once already).
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.delivery.api.matches import router as matches_router
from app.delivery.api.teams import router as teams_router
from app.delivery.services.match_service import MatchService
from app.delivery.services.pacer import Pacer
from app.delivery.services.team_service import TeamService
from app.persistence.database import DEFAULT_DATABASE_URL, create_engine_and_session_factory, init_models
from app.persistence.in_memory_repository import InMemoryMatchRepository
from app.persistence.sql_match_result_repository import SqlMatchResultRepository
from app.persistence.sql_team_repository import SqlTeamRepository


def create_app(database_url: str = DEFAULT_DATABASE_URL, pacer: Pacer | None = None) -> FastAPI:
    """`database_url`/`pacer` are parameters, not hardcoded globals, so
    tests can point this at an isolated in-memory database with a
    near-instant pace instead of a real, on-disk, real-time-paced one."""
    engine, session_factory = create_engine_and_session_factory(database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await init_models(engine)
        yield

    app = FastAPI(title="Global Soccer Manager", lifespan=lifespan)
    app.state.match_service = MatchService(
        InMemoryMatchRepository(),
        pacer=pacer,
        match_result_repository=SqlMatchResultRepository(session_factory),
    )
    app.state.team_service = TeamService(SqlTeamRepository(session_factory))
    app.include_router(matches_router)
    app.include_router(teams_router)
    return app


app = create_app()
