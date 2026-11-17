# Global Soccer Manager

![status](https://img.shields.io/badge/status-early%20development-orange)
![license](https://img.shields.io/badge/license-Apache%202.0-blue)
![python](https://img.shields.io/badge/backend-Python%203.12%2B-3776AB?logo=python&logoColor=white)

**An open-source football season simulator and team management game.**

Manage a club, build a squad, set your tactics, and live every match through
a fast-paced simulation — score, cards, injuries, and phase-by-phase drama.
An optional **React match viewer** renders a top-down pitch from real engine
coordinates (not a separate animation layer).

---

## Table of contents

- [Vision](#vision)
- [What makes a result](#what-makes-a-result)
- [Roadmap](#roadmap)
- [Architecture](#architecture)
- [Repository structure](#repository-structure)
- [Getting started](#getting-started)
- [Submission checklist (take-home)](#submission-checklist-take-home)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## Vision

Global Soccer Manager is built around one core idea: a **match simulation
engine** that produces a live, narrated match experience in the spirit of
classic text-based football sims — think "player enters the box... shoots...
**GOAL!**" rather than a 2D/3D animated pitch. On top of that engine, a full
management game will grow: squads, tactics, transfers, and season
progression.

The project is open source (Apache 2.0) from day one, built to be readable
and welcoming to contributors of all experience levels.

## What makes a result

Every match outcome is the product of three forces, deliberately kept in
balance so that none of them makes the others irrelevant:

| Pillar | Role |
|---|---|
| **Player quality** | Individual attributes — pace, passing, shooting, tackling, and more — drive every duel on the pitch. |
| **Tactics** | Mentality, tempo, pressing, width, defensive line, and marking scheme *structurally* change how a match unfolds, not just its odds. Tactics and substitutions can be changed **mid-match** and take effect on the very next play — proven by statistical test, not just claimed. |
| **Variance** | No duel is ever certain — probabilities are always clamped away from 0% and 100% — and rare, independent "moments of brilliance" mean even a modest player can occasionally produce a standout play. Home advantage and weather add further context on top. |

## Roadmap

The path to the full game runs through the match engine first — everything
else (squads, tactics UI, transfers, seasons) is built on top of it, so it
has to be right before anything else is worth building. Phases are meant to
be built roughly in order; later phases will get more detail as earlier ones
land.

**Phases 0–4 (engine, API, persistence, match viewer) are in place for the interview take-home. Season/league layers remain future work.**

<details>
<summary><b>Phase 0 — Foundations (design)</b></summary>

- [x] Vision & scope defined
- [x] Match engine architecture (possession chains, tactical matchup model,
      contest resolution formula)
- [x] Stats → rating algorithm design (`PhaseRatingCalculator`,
      `ProtagonistSelector`, data-driven weight tables)
- [x] API/streaming architecture (WebSocket live match delivery, deterministic
      engine decoupled from real-time pacing)
- [ ] Phase state machine as an extensible strategy/registry pattern (so new
      phases — extra time, penalty shootouts — don't require touching a
      central branch)
- [ ] `MatchEvent` schema versioning strategy (so new event types don't break
      already-deployed clients later)

</details>

<details>
<summary><b>Phase 1 — Match Engine MVP</b></summary>

The first real milestone: simulate a full match and print its commentary
feed from a script, no API or UI involved yet.

- [x] Backend scaffolding (`pyproject.toml`, folder skeleton)
- [x] Domain models (`Player`, `Team`, `Tactic`)
- [x] Rating layer (`PhaseRatingCalculator`, `ProtagonistSelector`, weight
      tables)
- [x] Possession-chain engine (phase transitions, contest resolution,
      fatigue, tactical matchup)
- [x] Moments of brilliance (rare, flair-driven individual spikes — not the
      same thing as the smooth team/individual stat blend)
- [x] Home advantage & weather as match-context modifiers
- [x] Live mid-match tactic changes and substitutions (`Match` class),
      proven by statistical test to measurably change outcomes — not just
      accepted as input and ignored
- [x] Fouls, cards, injuries (a foul is a free kick — the attacking team
      keeps the ball, not a turnover; second yellow becomes red; red
      cards/injuries take a player out for the rest of the match)
- [x] AI-driven automatic substitutions (injury always tries a like-for-like
      bench player; tiredness subs off the single most fatigued eligible
      starter; both respect a 5-substitution limit; never triggered by a
      red card, matching real football)
- [x] Commentary generation (template banks, attribute-flavored phrasing
      for progression/shot/foul events) — `scripts/menu.py` narrates full
      matches now
- [x] Statistical/balance test suite (now also covering brilliance, home
      advantage, weather, mid-match control, fouls/cards/injuries, and
      commentary)
- [x] **Milestone:** simulate a match from the command line and read a
      narrated commentary feed end to end (`python backend/scripts/menu.py`,
      or `python backend/scripts/simulate_demo.py` for the raw event feed)
- [ ] CI basics

Calibration note: a possession chain requires winning several *sequential*
contests, so per-duel probabilities compound multiplicatively — an early
pass at the contest formula's constants let a 15-point attribute gap alone
produce a 93% win rate for the favorite with the underdog winning under 1%
of the time. Constants were re-tuned empirically against the statistical
tests; see the calibration note in `backend/app/engine/probability.py` for
the full story and current values.

</details>

<details>
<summary><b>Phase 2 — Live Delivery</b></summary>

- [x] FastAPI REST + WebSocket layer (`api/`/`services/` split)
- [x] `Pacer` for live-paced match streaming (fixed pace, injectable for
      tests)
- [x] Multi-viewer session handling (one simulation, many watchers, proven
      by test — a late viewer gets the full backlog then joins live)
- [x] In-memory `MatchRepository` behind an interface (Phase 3 will add a
      real database implementation, not touching services/routes)
- [x] **Milestone:** create a match via `POST /matches` and watch it live
      over WebSocket, narrated with commentary, from a simple client
      (`fastapi.testclient.TestClient` in `tests/delivery/`, or a real
      WebSocket client against `uvicorn app.main:app`)
- [x] A minimal manual/CLI WebSocket client script
      (`backend/scripts/live_client.py`) — watch a real match live through
      the actual API/WebSocket contract, real-time paced, no second
      terminal needed

</details>

<details open>
<summary><b>Phase 3 — Persistence</b></summary>

- [x] Choose a database — SQLite (async, via SQLAlchemy + `aiosqlite`);
      zero setup, upgradeable to PostgreSQL later behind the same
      repository interfaces without touching services/routes
- [x] Repository interfaces + implementations for teams (with their full
      roster) and match results — no standalone player repository yet
      (a player only exists as part of a team; free agents/transfers are
      Phase 7)
- [x] Fictional player/team generation tooling (`TeamGenerator`,
      `scripts/seed_database.py`) — no real-world player data, this is an
      original, license-clean simulator
- [x] **Milestone:** `POST /teams` to persist a roster, `GET /teams/{id}`
      to fetch it back, and `GET /matches/{id}/result` for a finished
      match's score + full event log — all still there after a restart
- [ ] Migrations (Alembic) — schema still moves too fast to be worth it
      yet; tables are just recreated on startup for now

</details>

<details>
<summary><b>Phase 4 — Frontend MVP</b></summary>

- [ ] Pick the frontend stack
- [ ] Live match viewer: score, clock, event ticker, commentary feed
- [ ] Basic team/squad browsing UI

</details>

<details>
<summary><b>Phase 5 — Club & Tactics Management</b></summary>

- [ ] Squad management UI (players, attributes, fitness)
- [ ] Formation & tactics editor, wired to actually change simulated matches
- [ ] Save/load tactics per team

</details>

<details>
<summary><b>Phase 6 — Seasons & Competitions</b></summary>

- [ ] Fixture/schedule generation
- [ ] League table & standings
- [ ] Simulate a full matchday/season, not just a single match
- [ ] Cup/knockout competitions

</details>

<details>
<summary><b>Phase 7 — Club Economy</b></summary>

- [ ] Transfer market
- [ ] Contracts & wages
- [ ] Club finances/budget

</details>

<details>
<summary><b>Phase 8 — Progression & Depth</b></summary>

- [ ] Player development/aging across seasons
- [ ] Morale system
- [ ] Persistent injuries across matches
- [ ] Training

</details>

<details>
<summary><b>Phase 9 — Community & Polish</b></summary>

- [ ] CI/CD and test coverage gates
- [ ] Contributing guide, issue templates
- [ ] Docker/dev environment setup
- [ ] Deployment guide

</details>

## Architecture

At a glance:

```
 Client (frontend, TBD)
        │  WebSocket (live, commentary-annotated match events)
        ▼
 delivery/api      →  thin FastAPI routes (POST /matches, WS /stream)
        │
        ▼
 delivery/services →  MatchService/TeamService: session lifecycle, Pacer,
        │                persistence/ (SQLite, behind an interface —
        │                live event log in-memory, results/teams durable)
        ▼
 engine + commentary →  pure, deterministic match simulation, narrated
        │
        ▼
 domain            →  Player, Team, Formation, Tactic
```

The simulation engine is a plain, seeded, synchronous step function — it
knows nothing about WebSockets or real time. A separate `Pacer` component
(the only place `asyncio.sleep` is allowed) paces its output for live
viewers, which means the exact same engine code can run a single
live-streamed match or simulate thousands of matches instantly for balance
testing, with identical, reproducible results. Multiple viewers of the same
match share one simulation — the engine is never re-invoked per viewer.

## Repository structure

```
backend/
  app/
    domain/       - Player, Team, Formation, Tactic
    engine/       - the match simulation engine
    commentary/   - turns match events into narrative text
    delivery/
      api/        - FastAPI routes (matches.py, teams.py)
      services/   - orchestration (MatchService, TeamService, Pacer)
      schemas.py  - Pydantic wire models + domain conversion
    persistence/  - SQLite (async): MatchRepository (live, in-memory),
                    TeamRepository + MatchResultRepository (durable, SQL)
    generation/   - fictional player/team content (no real-world data)
    main.py       - FastAPI app factory (`uvicorn app.main:app`)
  tests/
    delivery/     - FastAPI TestClient tests (REST + WebSocket)
    persistence/  - repository round-trip tests (isolated in-memory SQLite)
    generation/   - generator determinism/distribution tests
frontend/app/     - React + TypeScript + Vite match viewer
```

## Getting started

**Prerequisites:** Python **3.12+**, Node **16+** (18+ recommended for newest Vite).

### Backend (Windows PowerShell)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

# Tests (pytest is inside .venv — not on PATH until activated)
.\.venv\Scripts\pytest.exe -q

# One match to stdout
.\.venv\Scripts\python.exe scripts\simulate_demo.py

# Batch calibration (100 seeded matches)
.\.venv\Scripts\python.exe scripts\batch_simulate.py -n 100 -o ..\docs\batch_calibration_results.json

# API server (use 127.0.0.1; pick another port if 8000 is blocked)
.\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open **http://127.0.0.1:8000/docs** for interactive REST docs.

### Backend (macOS / Linux)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
python scripts/simulate_demo.py
python scripts/batch_simulate.py -n 100 -o ../docs/batch_calibration_results.json
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend match viewer (Windows)

Requires the **backend** running on port **8000** (Vite proxies `/api` to it).

```powershell
cd frontend\app
npm install
npm run dev
```

Open **http://127.0.0.1:5173** — click **New controlled match**, then use **+1 chain** / manager controls.

If port 8000 fails with `WinError 10013`, stop any old server (`netstat -ano | findstr :8000`) or use:

```powershell
.\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8010 --reload
```

Create `frontend/app/.env`:

```env
VITE_API_BASE=http://127.0.0.1:8010
VITE_WS_BASE=ws://127.0.0.1:8010
```

Restart `npm run dev`.

### Useful scripts

| Command | Purpose |
|--------|---------|
| `python scripts/menu.py` | Interactive scenarios with commentary |
| `python scripts/seed_database.py` | Seed SQLite with fictional teams |
| `python scripts/live_client.py` | CLI WebSocket client for auto matches |

## Submission checklist (take-home)

Verified on this repo **2026-11-16** (Windows, project venv):

| Check | How verified | Result |
|-------|----------------|--------|
| Backend tests | `.\.venv\Scripts\pytest.exe -q` | **113 passed**, 2 warnings, ~60s |
| Headless batch (100 seeds) | `batch_simulate.py -n 100` | Goals/match mean **3.17** — see [`docs/batch_calibration_results.json`](docs/batch_calibration_results.json) |
| Full match (script) | `simulate_demo.py` | Event log through **full_time** |
| REST + controlled manager API | `tests/delivery/test_controlled_matches_api.py` + inline audit | advance, pause/resume, tactics, subs, statistics, result |
| WebSocket stream | `tests/delivery/test_matches_api.py` | kickoff → events → full_time |
| Deterministic replay | `tests/engine/test_batch_calibration.py` | same seed → same events; snapshot resume → same finish |
| Frontend build | `cd frontend/app && npm run build && npm test` | build OK; **2** Vitest tests passed |

**Not verified automatically in CI:** manual browser click-through of the React UI (build + API proxy are verified; you should confirm visuals locally).

### Implemented (interview scope)

- Deterministic possession-chain match engine (11v11, seeded RNG)
- Match clock with half-time and stoppage time
- Validated formations; tactical pitch coordinates on events
- Live stats (goals, shots, possession chains, pass completion proxy, fouls, cards)
- FastAPI: auto and **controlled** matches; WebSocket commentary stream
- Manager endpoints: advance (steps, target minute, next key event, until full time), pause/resume, tactics, formation, substitutions, statistics
- **REST snapshot** `GET/POST /matches/{id}/snapshot`, `POST /matches/{id}/restore` (wraps `match_snapshot.py`)
- Structural **offside** and **penalty** mechanics (simplified; not full IFAB)
- Enriched **match result** payload: statistics, player end states, evidence-based summary bullets
- WebSocket events include monotonic **`index`** for reliable deduplication
- React viewer: scoreboard (clock/stoppage/cards), pitch, commentary, team + player stats, full tactic/formation controls

### Known limitations (honest)

- **Not full IFAB 2026/27 compliance** — offside/penalties are structural approximations; no throw-ins, goal kicks as real restarts, extra time, etc.
- **Phase-based simulation**, not continuous physics; pass counts remain a possession-chain proxy, not individual pass tracking
- **No dedicated replay HTTP route** — determinism via same seed (+ snapshot restore); tactical action replay requires recorded manager actions
- **No** xG model, heat maps, leagues, transfers, or auth
- **Manager `advance` on auto matches** returns 400 (by design)
- **Formation change** must match the current lineup shape (e.g. 4-3-3 slots)
- **SQLite** match results persist; live in-progress sessions are in-memory only

### Incomplete vs original take-home wish-list

- Durable in-progress match DB (snapshots are REST + in-memory session today), dedicated replay route, substitution windows (3 windows + HT), 1000-match CI calibration, corners/interceptions as distinct events, full pitch animation, production Docker/CI

Edit `scripts/simulate_demo.py`, or add a scenario to `scripts/menu.py`, to
try your own team stats/tactics and see how a match plays out.

## Documentation

Design decisions and detailed technical specs live alongside the code as
`CLAUDE.md` files, one per area of the project:

- [`docs/MATCH_ENGINE_NOTES.md`](docs/MATCH_ENGINE_NOTES.md) — plain-language
  walkthrough of how the match engine works today
- [`docs/batch_calibration_results.json`](docs/batch_calibration_results.json) —
  latest headless batch summary (goals, shots, possession, passes, cards)
- [`CLAUDE.md`](CLAUDE.md) — project vision, structure, and conventions
- [`backend/CLAUDE.md`](backend/CLAUDE.md) — backend stack and code conventions
- [`backend/app/engine/CLAUDE.md`](backend/app/engine/CLAUDE.md) — the match simulation engine, in depth
- [`backend/app/commentary/CLAUDE.md`](backend/app/commentary/CLAUDE.md) — narrative commentary generation
- [`backend/app/delivery/CLAUDE.md`](backend/app/delivery/CLAUDE.md) — API and live match streaming
- [`frontend/CLAUDE.md`](frontend/CLAUDE.md) — match viewer (React/Vite)
- [`frontend/app/README.md`](frontend/app/README.md) — run the UI locally

## Contributing

The project isn't yet at a stage where external contributions can be merged
predictably — the core engine architecture is still being locked down.
Watch/star the repo to follow progress; a contributing guide will land once
there's a working engine MVP to build on.

## License

Licensed under the [Apache License 2.0](LICENSE).
