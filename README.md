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
- [Project status](#project-status)
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
| **Tactics** | Mentality, tempo, pressing, width, defensive line, and marking scheme *structurally* change how a match unfolds, not just its odds. Two teams with identical players but opposed tactics should play visibly different matches. |
| **Variance** | No duel is ever certain. Probabilities are always clamped away from 0% and 100%, and the dice still has to be rolled — upsets are a feature, not a bug. |

## Project status

Currently in the **design phase**, focused entirely on the backend match
engine. No gameplay code has been written yet — the priority right now is
getting the simulation architecture right before writing implementation.

- [x] Project vision and scope defined
- [x] Match engine architecture designed (possession-chain simulation,
      tactical matchup model, contest resolution formula)
- [x] API/streaming architecture designed (WebSocket live match delivery)
- [ ] Backend scaffolding (project skeleton, domain models)
- [ ] Match engine implementation
- [ ] API + live match streaming implementation
- [ ] Frontend (stack not yet chosen)
- [ ] Persistence layer
- [ ] Season/league/transfer systems

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

There's nothing runnable yet — the project is still in the architecture and
design-documentation stage. Once the backend scaffolding lands, this section
will cover installing dependencies and running the API locally.

## Documentation

Design decisions and detailed technical specs live alongside the code as
`CLAUDE.md` files, one per area of the project:

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
