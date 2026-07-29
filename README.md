# Global Soccer Manager

![status](https://img.shields.io/badge/status-early%20development-orange)
![license](https://img.shields.io/badge/license-Apache%202.0-blue)
![python](https://img.shields.io/badge/backend-Python%203.12%2B-3776AB?logo=python&logoColor=white)

**An open-source football season simulator and team management game.**

Manage a club, build a squad, set your tactics, and live every match through
a fast-paced, text-driven simulation — no pitch graphics, just score,
cards, injuries, and the tension of every attack unfolding phase by phase.

---

## Table of contents

- [Vision](#vision)
- [What makes a result](#what-makes-a-result)
- [Roadmap](#roadmap)
- [Architecture](#architecture)
- [Repository structure](#repository-structure)
- [Getting started](#getting-started)
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

**🚧 Currently in: Phase 0 (design), moving into Phase 1.**

<details open>
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

<details open>
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

- [ ] FastAPI REST + WebSocket layer (`api/`/`services/` split)
- [ ] `Pacer` for live-paced match streaming
- [ ] Multi-viewer session handling (one simulation, many watchers)
- [ ] **Milestone:** watch a full match live over WebSocket from a simple
      client

</details>

<details>
<summary><b>Phase 3 — Persistence</b></summary>

- [ ] Choose a database (likely PostgreSQL)
- [ ] Repository interfaces + implementations for players, teams, match
      results
- [ ] Fictional player/team generation tooling (no real-world player data —
      this is an original, license-clean simulator)

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
        │  WebSocket (live match events)
        ▼
 delivery/api      →  thin FastAPI routes
        │
        ▼
 delivery/services →  MatchService: session lifecycle, pacing
        │
        ▼
 engine            →  pure, deterministic match simulation
        │
        ▼
 domain            →  Player, Team, Formation, Tactic
```

The simulation engine is a plain, seeded, synchronous generator — it knows
nothing about WebSockets or real time. A separate `Pacer` component paces its
output for live viewers, which means the exact same engine code can run a
single live-streamed match or simulate thousands of matches instantly for
balance testing, with identical, reproducible results.

## Repository structure

```
backend/
  app/
    domain/       - Player, Team, Formation, Tactic
    engine/       - the match simulation engine
    commentary/   - turns match events into narrative text
    delivery/
      api/        - FastAPI routes
      services/   - orchestration (MatchService, session lifecycle)
    persistence/  - repository interfaces (in-memory for now)
  tests/
frontend/         - not started yet
```

## Getting started

The match engine has a first runnable slice — no API/frontend yet, just the
simulation itself.

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest                       # unit + statistical balance tests
python scripts/simulate_demo.py   # simulate one match, print its event feed
python scripts/menu.py            # interactive scenario picker, incl. live
                                   # mid-match tactic changes/substitutions
```

Edit `scripts/simulate_demo.py`, or add a scenario to `scripts/menu.py`, to
try your own team stats/tactics and see how a match plays out.

## Documentation

Design decisions and detailed technical specs live alongside the code as
`CLAUDE.md` files, one per area of the project:

- [`docs/MATCH_ENGINE_NOTES.md`](docs/MATCH_ENGINE_NOTES.md) — plain-language
  walkthrough of how the match engine works today
- [`CLAUDE.md`](CLAUDE.md) — project vision, structure, and conventions
- [`backend/CLAUDE.md`](backend/CLAUDE.md) — backend stack and code conventions
- [`backend/app/engine/CLAUDE.md`](backend/app/engine/CLAUDE.md) — the match simulation engine, in depth
- [`backend/app/commentary/CLAUDE.md`](backend/app/commentary/CLAUDE.md) — narrative commentary generation
- [`backend/app/delivery/CLAUDE.md`](backend/app/delivery/CLAUDE.md) — API and live match streaming
- [`frontend/CLAUDE.md`](frontend/CLAUDE.md) — frontend status (pending)

## Contributing

The project isn't yet at a stage where external contributions can be merged
predictably — the core engine architecture is still being locked down.
Watch/star the repo to follow progress; a contributing guide will land once
there's a working engine MVP to build on.

## License

Licensed under the [Apache License 2.0](LICENSE).
