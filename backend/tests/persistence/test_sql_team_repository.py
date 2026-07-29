"""Round-trip tests for SqlTeamRepository against an isolated in-memory
SQLite database per test (never a shared/global engine — the same class
of cross-test state leak this project has hit before with plain Python
objects). No pytest-asyncio dependency: each async call is driven with a
plain asyncio.run() from an otherwise-ordinary sync test function.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from factories import build_team, make_player

from app.domain.player import Position
from app.persistence.database import create_engine_and_session_factory, init_models
from app.persistence.sql_team_repository import SqlTeamRepository


def _run(coro):
    return asyncio.run(coro)


def _new_repository() -> SqlTeamRepository:
    async def setup() -> SqlTeamRepository:
        engine, session_factory = create_engine_and_session_factory("sqlite+aiosqlite:///:memory:")
        await init_models(engine)
        return SqlTeamRepository(session_factory)

    return _run(setup())


def test_save_and_get_round_trips_a_full_team():
    repository = _new_repository()
    team = build_team("home", "FC Home", overall=65)

    _run(repository.save(team))
    fetched = _run(repository.get("home"))

    assert fetched.id == team.id
    assert fetched.name == team.name
    assert len(fetched.starting_xi) == 11
    assert len(fetched.bench) == 5
    assert fetched.tactic == team.tactic


def test_get_unknown_team_returns_none():
    repository = _new_repository()
    assert _run(repository.get("nope")) is None


def test_player_attributes_and_position_round_trip_exactly():
    repository = _new_repository()
    team = build_team("home", "FC Home", overall=60)
    team.starting_xi[9] = make_player("home_star", "Star", Position.ST, overall=60, shooting=95, pace=88)

    _run(repository.save(team))
    fetched = _run(repository.get("home"))

    star = next(p for p in fetched.starting_xi if p.id == "home_star")
    assert star.position == Position.ST
    assert star.attributes.shooting == 95
    assert star.attributes.pace == 88


def test_bench_players_are_distinguished_from_starters():
    repository = _new_repository()
    team = build_team("home", "FC Home", overall=60)

    _run(repository.save(team))
    fetched = _run(repository.get("home"))

    fetched_bench_ids = {p.id for p in fetched.bench}
    fetched_starter_ids = {p.id for p in fetched.starting_xi}
    assert fetched_bench_ids == {p.id for p in team.bench}
    assert not fetched_bench_ids & fetched_starter_ids


def test_list_all_returns_every_saved_team():
    repository = _new_repository()
    _run(repository.save(build_team("a", "Team A", overall=60)))
    _run(repository.save(build_team("b", "Team B", overall=60)))

    teams = _run(repository.list_all())

    assert {t.id for t in teams} == {"a", "b"}
