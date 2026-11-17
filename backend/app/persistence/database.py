"""Async SQLAlchemy engine/session setup. Only repositories (team_repository.py,
match_result_repository.py) ever import from here or from models.py —
services and routes depend on the repository interfaces, never on
SQLAlchemy directly (backend/CLAUDE.md).

`create_engine_and_session_factory()` takes the database URL as an
argument rather than reading a module-level global: every repository this
session builds gets its own engine/session factory, injected at
construction, so tests can point at an isolated in-memory database without
leaking state between runs (the same class of bug this project hit
several times already with shared mutable objects — see engine/CLAUDE.md
§8 and §5's story). `app/main.py` is the one place that picks the real,
on-disk URL for actual runs.
"""

from sqlalchemy import event, inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///./global_soccer_manager.db"


class Base(DeclarativeBase):
    pass


def create_engine_and_session_factory(database_url: str = DEFAULT_DATABASE_URL):
    """For `sqlite+aiosqlite:///:memory:` (tests), StaticPool keeps the
    same in-memory database alive across the multiple connections
    SQLAlchemy opens per session — without it, each session would see a
    brand new, empty in-memory database."""
    engine_kwargs: dict = {}
    if "sqlite" in database_url:
        engine_kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
    if database_url.endswith(":memory:"):
        engine_kwargs["poolclass"] = StaticPool

    engine = create_async_engine(database_url, **engine_kwargs)

    if "sqlite" in database_url:

        @event.listens_for(engine.sync_engine, "connect")
        def _sqlite_pragmas(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return engine, session_factory


async def init_models(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

        def _ensure_team_formation_column(sync_conn) -> None:
            if "sqlite" not in str(engine.url):
                return
            if "teams" not in inspect(sync_conn).get_table_names():
                return
            columns = {c["name"] for c in inspect(sync_conn).get_columns("teams")}
            if "formation" not in columns:
                sync_conn.execute(
                    text("ALTER TABLE teams ADD COLUMN formation VARCHAR(16) NOT NULL DEFAULT '4-3-3'")
                )

        await connection.run_sync(_ensure_team_formation_column)
