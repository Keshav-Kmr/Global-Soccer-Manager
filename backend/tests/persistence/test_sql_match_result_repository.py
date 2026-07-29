import asyncio

from app.persistence.database import create_engine_and_session_factory, init_models
from app.persistence.match_result_repository import MatchResult
from app.persistence.sql_match_result_repository import SqlMatchResultRepository


def _run(coro):
    return asyncio.run(coro)


def _new_repository() -> SqlMatchResultRepository:
    async def setup() -> SqlMatchResultRepository:
        engine, session_factory = create_engine_and_session_factory("sqlite+aiosqlite:///:memory:")
        await init_models(engine)
        return SqlMatchResultRepository(session_factory)

    return _run(setup())


def test_save_and_get_round_trips_a_result():
    repository = _new_repository()
    result = MatchResult(
        match_id="m1", team_a_id="home", team_a_name="FC Home", team_b_id="away", team_b_name="FC Away",
        score_a=2, score_b=1, seed=42,
        events=[{"minute": 0, "type": "kickoff"}, {"minute": 90, "type": "full_time"}],
    )

    _run(repository.save(result))
    fetched = _run(repository.get("m1"))

    assert fetched == result


def test_get_unknown_result_returns_none():
    repository = _new_repository()
    assert _run(repository.get("nope")) is None
