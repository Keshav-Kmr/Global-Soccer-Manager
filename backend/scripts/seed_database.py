"""Populate the database with a handful of fictional teams, so there's
something to `POST /matches` with team ids instead of hand-writing a full
roster JSON body every time.

Run from backend/ (inside the venv):
    python scripts/seed_database.py
"""

import asyncio
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.domain.tactic import Mentality, Pressing, Tactic
from app.generation.team_generator import TeamGenerator
from app.persistence.database import DEFAULT_DATABASE_URL, create_engine_and_session_factory, init_models
from app.persistence.sql_team_repository import SqlTeamRepository

_TEAMS = [
    ("FC Fictional", 75, Tactic(mentality=Mentality.ATTACKING, pressing=Pressing.HIGH)),
    ("Athletic Invented", 68, Tactic()),
    ("Real Nonexistent", 62, Tactic(mentality=Mentality.DEFENSIVE, pressing=Pressing.LOW)),
    ("United Imaginary", 58, Tactic()),
]


async def main() -> None:
    engine, session_factory = create_engine_and_session_factory(DEFAULT_DATABASE_URL)
    await init_models(engine)

    generator = TeamGenerator(random.Random(0))
    repository = SqlTeamRepository(session_factory)

    for name, quality, tactic in _TEAMS:
        team = generator.generate(name, quality, tactic)
        await repository.save(team)
        print(f"Saved {team.name!r} (id={team.id}, quality~{quality})")


if __name__ == "__main__":
    asyncio.run(main())
