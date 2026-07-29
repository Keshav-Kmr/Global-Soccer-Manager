# Global Soccer Manager

Open-source football season simulator and team management game.

## Vision

A game where you manage a football club: squad, tactics, transfers, and season
progression. The centerpiece is a **match simulation engine** that produces a
text/event-driven match experience — score, cards, injuries, key moments,
tension ("player enters the box... shoots... GOAL!" or "saved!") — in the
spirit of Hattrick or classic Football Manager's text engine. This is **not**
a visual pitch/2D-animation simulator. There is no ball position, no player
coordinates on a field. The drama comes from well-paced narrative events, not
graphics.

## Current focus

We are building the **backend match simulation engine MVP only**. No frontend,
no persistence, no leagues/seasons/transfers yet. Everything else in this
document describes the eventual full scope, but active work should stay
scoped to what's described in `backend/app/engine/CLAUDE.md` until that MVP
is solid and validated.

## The three pillars of a result

Every match outcome must be explainable by exactly three interacting forces.
This is a hard product requirement, not an implementation detail — treat any
design that lets one pillar dominate to the point of making another
irrelevant as a bug:

1. **Player quality** — individual attributes (pace, passing, shooting,
   tackling, etc.) drive every duel.
2. **Tactics** — mentality, tempo, pressing, width, defensive line, marking
   scheme. Tactics must have a *structural* effect on how a match unfolds
   (which phases happen, how often, who is favored in them), not just a flat
   multiplier on the same outcome shape. Two teams with identical players but
   opposed tactics should produce visibly different matches.
3. **Variance (luck)** — no duel is ever 100% certain. A weaker team must
   retain a real chance to win. Luck is structural (probabilities are always
   clamped away from 0/1) and stochastic (the actual dice roll can defy the
   odds).

See `backend/app/engine/CLAUDE.md` for how this is implemented concretely.

## Repository structure

```
/CLAUDE.md                     - this file: project-wide vision & conventions
/backend/CLAUDE.md             - backend stack, layout, conventions
/backend/app/engine/CLAUDE.md  - the match simulation engine (core design doc)
/backend/app/commentary/CLAUDE.md - turning events into narrative text
/backend/app/delivery/CLAUDE.md   - API/WebSocket layer, live match streaming
/frontend/CLAUDE.md            - frontend status (not started yet)
```

Rule of thumb: before working in a subdirectory that has its own `CLAUDE.md`,
read that file first. It takes precedence over this root file for anything
specific to that area; this root file holds what applies project-wide.

## Conventions

- **Determinism first.** Every simulated match must be reproducible from a
  seed. This is essential both for testing and for the "share a wild match
  result" experience open-source users will want.
- **Open source, community-friendly.** Apache 2.0 licensed. Favor readable,
  well-documented code over clever code — contributors will range widely in
  experience.
- **English for all code, docs, and commit messages**, regardless of the
  language used in design discussions.
- Don't build ahead of what's actually being worked on. Sections of this
  document describing future scope (transfers, seasons, leagues, frontend)
  are context, not a backlog to start implementing.

## Explicitly out of scope for now

- Visual pitch rendering / 2D or 3D animation.
- Persistence layer (database) — will be decided once the engine MVP is
  stable.
- Frontend framework choice — deferred.
- Leagues, seasons, transfers, finances, youth academy, scouting — all future
  game-layer features built on top of the match engine, not part of it.
