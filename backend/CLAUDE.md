# Backend

## Stack

- **Python 3.12+**
- **FastAPI** — REST endpoints + native WebSocket support for live match
  streaming (see `app/delivery/CLAUDE.md`).
- **Pydantic** — all domain/data-transfer models (players, teams, tactics,
  match events). Gives us validation and a natural JSON schema for the
  WebSocket wire format for free.
- **pytest** — unit tests and statistical/balance tests (see below).

No database yet. No auth yet. Both are deliberately deferred until the engine
MVP is proven — don't design around them prematurely.

## Layout

```
backend/
  app/
    domain/            - pure data models: Player, Team, Formation, Tactic
    engine/            - the match simulation engine itself (see its CLAUDE.md)
      rating/          - stats -> phase ratings (see its own CLAUDE.md)
    commentary/        - MatchEvent -> narrative text
    delivery/
      api/             - FastAPI routers ONLY: parse request, call a service,
                         return/stream the response. No logic lives here.
      services/        - orchestration: MatchService owns match session
                         lifecycle, invokes the engine, runs the Pacer.
                         This is where routes' actual logic lives.
      schemas.py        - Pydantic request/response + WebSocket wire models
    persistence/
      repositories/     - repository interfaces (e.g. MatchRepository ABC) +
                         concrete implementations (in-memory now, DB later).
                         Services depend on the interface, never on a
                         concrete DB client directly.
  tests/
    engine/            - unit + statistical tests for the simulation
    ...
  pyproject.toml
```

`domain/` has no dependency on FastAPI, Pydantic-for-API-purposes, or anything
in `delivery/`. It should be importable and testable in complete isolation —
this is what makes it possible to run 10,000 simulated matches in a script
for balance-tuning without spinning up a server.

## Code style & architecture conventions

These apply everywhere in `backend/`, not just one module:

- **Layered, one-way dependencies**: `api/` (routes) -> `services/`
  (orchestration/logic) -> `domain/` + `engine/` + `persistence/`
  (repository interfaces). A route handler should be a few lines: parse
  input, call a service method, shape the output. Business logic that ends
  up in a route function is a signal it belongs in a service class instead.
- **DB access is never reachable from routes or from `engine/`/`commentary/`
  directly.** Only `services/` talk to `persistence/` repositories, and only
  through an interface (e.g. an abstract `MatchRepository`), never a
  concrete database client. This is what lets us ship the whole engine MVP
  with an in-memory repository and swap in Postgres later without touching
  routes, services call-sites, or the engine.
- **Class-based design for anything with behavior or configuration.**
  Stateless pure data (DTOs, wire schemas) can be plain Pydantic
  models/dataclasses, but simulation components, services, and repositories
  should be classes with a clear single responsibility and an explicit
  public interface — e.g. `MatchSimulator`, `ProbabilityModel`,
  `PossessionChainEngine`, `MatchService`, `MatchRepository`. Avoid loose
  module-level functions accumulating unrelated logic; if a module has more
  than one clear responsibility, split it.
- **One class (or a small set of tightly related classes) per file.** A file
  name should tell you what class lives in it. Avoid growing a single file
  into a dumping ground for the whole layer.
- **Every public class and method gets a docstring** explaining *why*/what
  role it plays, not a restatement of the code (e.g. not "gets the player
  name" for `get_player_name()`). If a docstring would just repeat the
  method name, skip it and rely on the name instead — but any non-obvious
  behavior, invariant, or formula (see the contest formula in
  `engine/CLAUDE.md`) must be documented at the class or method level.
- **Folder structure mirrors responsibility, not file type.** Don't create
  generic dumping grounds like `utils/` or `helpers/`; if something doesn't
  obviously belong to `domain/`, `engine/`, `commentary/`, `delivery/`, or
  `persistence/`, that's a sign it needs its own clearly named module.

## Determinism rule

Never call the module-level `random` functions (`random.random()`,
`random.choice()`, ...) anywhere in `engine/` or `commentary/`. Always thread
a single `random.Random(seed)` instance through the whole simulation of one
match, from kickoff to full time, including commentary template selection.
Two calls to `simulate_match(team_a, team_b, tactics, seed=42)` must produce
byte-identical event streams.

## Testing philosophy

Two kinds of tests, both required for anything touching the probability
model:

1. **Unit tests** on isolated contest formulas — given known inputs, assert
   the output probability/outcome is what the formula should produce.
2. **Statistical/regression tests** — run N simulations (hundreds to
   thousands) of a scenario and assert aggregate properties fall in an
   expected range, e.g. "a team with all attributes +20 over its opponent
   should win significantly more than 50% of the time, but not more than
   ~90%" or "average goals per game across many simulations should land in a
   realistic band (order of 2.5-3 total)." These are the tests that actually
   validate game balance, not just code correctness.

Run tests with `pytest`. Any change to `engine/` that touches probabilities
should include or update a statistical test, not just unit tests on the
happy path.
