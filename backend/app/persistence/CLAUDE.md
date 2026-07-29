# Persistence

SQLite (async, via SQLAlchemy + `aiosqlite`). Services depend on repository
*interfaces* here, never on SQLAlchemy or a concrete store directly
(backend/CLAUDE.md) — that's what lets the database engine change later
without touching `delivery/services/` or any route.

## Two repositories, two very different lifetimes

- **`MatchRepository`** (`repository.py` + `in_memory_repository.py`) — the
  *live*, in-progress event log for a match currently streaming, used by
  `MatchService`/`delivery/api/matches.py`'s WebSocket route. Pure
  in-memory, on purpose: it holds ephemeral, real-time state nobody needs
  to survive a process restart, and writing every single event to disk as
  it's produced would be needless I/O for a match that's still running.
- **`MatchResultRepository`** (`match_result_repository.py` +
  `sql_match_result_repository.py`) — the *durable* record of a **finished**
  match: final score, participants, and the full commentary-annotated
  event log, stored once when `MatchService` sees `match.finished` become
  true. This is what makes `GET /matches/{id}/result` work even after a
  server restart, unlike `/stream`.

Don't merge these into one repository — they exist for different reasons,
change at different rates (many small live appends vs. one write at the
end), and one being in-memory while the other is durable is deliberate,
not an inconsistency to "fix."

## `TeamRepository`

`team_repository.py` (interface) + `sql_team_repository.py` (SQLAlchemy
implementation). Persists a `Team`'s full roster (`starting_xi` + `bench`)
and its `Tactic`. A player only exists as part of a team right now — no
free-agent pool, no transfers (that's README roadmap Phase 7) — so there's
no standalone `PlayerRepository`; `PlayerModel` is a plain child table of
`TeamModel` in `models.py`.

`SqlTeamRepository` is the *only* code that converts between domain
`Team`/`Player`/`Tactic` objects and `TeamModel`/`PlayerModel` ORM rows —
this conversion logic belongs to the repository, not to `domain/` (which
stays framework-free) or `delivery/schemas.py` (a different, wire-facing
conversion, from/to JSON, not from/to SQL rows). Three layers, three
separate translations, on purpose — see backend/CLAUDE.md's layering rule.

## Testability: inject the database, don't hardcode it

`database.py`'s `create_engine_and_session_factory(database_url)` takes
the URL as an argument, and `app/main.py:create_app()` forwards its own
`database_url` parameter down to it, rather than either reading a
module-level global. This is the same fix, for the same reason, applied
repeatedly elsewhere in this project (`engine/match.py`'s `Team` snapshot
story is the clearest example): a hardcoded/shared database would leak
state between independent test runs the same way shared `Team`/`Player`
objects once did. Tests always pass `sqlite+aiosqlite:///:memory:` — see
`create_engine_and_session_factory`'s `StaticPool` handling for why
in-memory SQLite specifically needs that (SQLAlchemy's normal pooling
opens a new connection per session, and a new connection to `:memory:` is
a brand new, empty database — `StaticPool` keeps one connection, and
therefore one database, alive for the engine's lifetime).

No `pytest-asyncio` dependency: repository tests drive each async call
with a plain `asyncio.run(...)` from an ordinary sync `def test_...():`
function — enough for straightforward request/response-shaped async code,
without adding a plugin and its `asyncio_mode` configuration for what
these tests actually need.

## Migrations

None yet — `init_models()` just calls `Base.metadata.create_all()` on
startup. Fine while the schema is still moving fast; a project this early
doesn't need Alembic's ceremony yet. Revisit once the schema stabilizes and
an actual migration (not just "recreate the dev database") is needed.

## Fictional content generation

Not persistence itself, but persistence's most immediate customer: this
project uses **no real-world player data** (root CLAUDE.md, README) — see
`app/generation/team_generator.py` (`TeamGenerator`/`PlayerGenerator`) for
how seeded content is procedurally invented instead, and
`scripts/seed_database.py` for populating the database with a handful of
generated teams. Generation takes a `random.Random` the same way the
engine does, including for ids (`uuid.uuid4()` would silently break that
determinism — it reads from `os.urandom`, not the seeded generator).

## Explicitly out of scope for now

- A `PlayerRepository` independent of `Team` (transfers/free agents, Phase 7).
- Alembic / real schema migrations.
- Anything beyond SQLite — swapping the engine (e.g. to PostgreSQL) should
  only ever mean changing the URL passed to `create_engine_and_session_factory`
  and the driver dependency, not the repository interfaces or their callers.
