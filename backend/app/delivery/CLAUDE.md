# Delivery (API + live streaming)

Exposes the match engine over HTTP/WebSocket. This layer owns *timing* and
*transport*; it must not contain any simulation logic or probability code —
that all lives in `app/engine`.

## Internal structure: routes vs. logic

Per the architecture convention in `backend/CLAUDE.md`, `delivery/` is split
so routes never carry logic:

- `delivery/api/` — FastAPI routers only. A route function parses the
  request, calls a `MatchService` method, and returns/streams the result.
  Nothing else. If you find yourself writing an `if`/loop that isn't about
  HTTP/WebSocket mechanics inside a route function, it belongs in
  `services/` instead.
- `delivery/services/` — `MatchService` is the class that actually owns
  match session lifecycle: starting a simulation, running the `Pacer`,
  maintaining the in-memory event log, and handing new/late viewers what
  they need. Routes call into this; the engine is only ever invoked from
  here, never from a route directly.
- `delivery/schemas.py` — Pydantic models for REST request/response bodies
  and the WebSocket wire format (the JSON shape below). Kept separate from
  `app/domain` models, which describe the simulation's internal world, not
  the wire contract.

`MatchService` depends on a `MatchRepository` interface from
`app/persistence` for anything that needs to persist beyond the current
process — never on a concrete database client directly (see
`backend/CLAUDE.md`).

## Why streaming doesn't compromise determinism

The engine (`simulate_match`) is a plain synchronous generator with no
concept of real time. Delivery wraps it with a **Pacer** that consumes the
generator and forwards each event over the network with a delay. This means:

- The exact same engine call can run to completion instantly (used in tests,
  balance simulations, "simulate 1000 matches" tooling) or be paced out live
  for a viewer — same code path, same determinism, two different consumers.
- The Pacer is the only place that deals with `asyncio.sleep` / wall-clock
  time. Keep it that way.

## REST

`POST /matches` — create and start a match.

```json
{
  "team_a": { ... },
  "team_b": { ... },
  "seed": 42          // optional; random if omitted, but recorded either way
}
```

Response: `{ "match_id": "..." }`. Starting the match kicks off the
simulation server-side immediately (see "session lifecycle" below) — it does
not wait for a WebSocket client to connect.

## WebSocket

`GET /matches/{match_id}/stream` — connect to receive events as they're
paced out.

Wire format per message (mirrors `MatchEvent` from the engine, plus the
rendered commentary line):

```json
{
  "minute": 34,
  "type": "SHOT",
  "team": "team_a",
  "players": ["player_id_123"],
  "payload": { "shot_quality": "good" },
  "commentary": "Dubois dances past a challenge and gets a shot away!"
}
```

## Session lifecycle

A match is simulated **once**, server-side, regardless of how many clients
watch it. Session state:

- On `POST /matches`, the full event stream starts generating in a
  background task and is appended to an in-memory event log for that
  `match_id` as it's produced (paced by the same Pacer that would feed a
  live WebSocket, so "live" is really just "currently appending").
- A WebSocket client connecting mid-match first receives the backlog (all
  events so far, sent quickly, no artificial delay) and then continues
  receiving new events live at normal pace.
- Multiple simultaneous viewers of the same `match_id` all read from the
  same event log — the engine is never re-invoked per viewer.

This keeps the MVP simple (in-memory, single-process) while still behaving
correctly for the "multiple people watching the same match" case, which is
core to what makes this a shared/social simulator rather than a single-player
toy.

## Pace configuration

v1: a single fixed pace (e.g. real_seconds_per_game_minute as a constant).
Speed multipliers (2x, instant-replay) and per-viewer pace are plausible
follow-ups, not MVP scope — don't build a generalized pacing config system
before there's a concrete need for it.

## Explicitly out of scope for MVP

- Authentication / authorization.
- Reconnection tokens / resuming a dropped connection beyond simple
  reconnect-and-get-backlog.
- Persisting finished matches to a database (the in-memory event log is
  ephemeral for now — see root `CLAUDE.md` on persistence being deferred).
- Horizontal scaling / multi-process match session sharing.
