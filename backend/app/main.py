"""FastAPI application factory.

Run locally (from backend/, with the venv active):
    uvicorn app.main:app --reload

`MatchService`/`InMemoryMatchRepository` are constructed once here and
stashed on `app.state` — this is the single source of truth for a
request's/WebSocket's `Depends(get_match_service)` (delivery/api/matches.py),
so every viewer of a given match shares the same running simulation.
"""

from fastapi import FastAPI

from app.delivery.api.matches import router as matches_router
from app.delivery.services.match_service import MatchService
from app.persistence.in_memory_repository import InMemoryMatchRepository


def create_app() -> FastAPI:
    app = FastAPI(title="Global Soccer Manager")
    app.state.match_service = MatchService(InMemoryMatchRepository())
    app.include_router(matches_router)
    return app


app = create_app()
