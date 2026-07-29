# Session notes — Match simulation engine

This document summarizes, in plain and pedagogical terms, what's been
designed and built so far. It's a memory aid for you, not a technical
spec — for exact detail meant for coding, see the `CLAUDE.md` files listed
at the bottom of this document.

**Where things stand**: the match simulation engine, a live API/WebSocket
layer, and SQLite persistence are all functional and tested (backend only
— no frontend yet). You can simulate a full match between two teams with
custom stats in the terminal, or create/watch one live over the real API.

---

## 1. The game concept

An open-source football season simulator + team management game. The
centerpiece (what we're working on) is a **text match simulation engine**
— not a visual pitch, but an event feed with tension ("he enters the
box... he shoots... GOAL!" or "missed!"), in the spirit of old text-based
management games (Hattrick, text-era Football Manager).

### The three pillars of a result

Every match outcome must be explainable by three interacting forces,
deliberately balanced so none of them overrides the others:

1. **Player quality** — their individual attributes.
2. **Tactics** — must have a real structural effect, not just a cosmetic
   one. Can be changed **mid-match** with immediate effect.
3. **Luck** — no duel is ever guaranteed, plus rare moments of brilliance.

---

## 2. Project structure

```
Global-Soccer-Manager/
├── CLAUDE.md                       # project vision, general conventions
├── README.md                       # full roadmap (10 phases), public doc
├── docs/
│   └── MATCH_ENGINE_NOTES.md       # this file
├── backend/
│   ├── CLAUDE.md                   # backend conventions (layers, code style)
│   ├── pyproject.toml
│   ├── conftest.py                 # makes `app` importable for pytest
│   ├── app/
│   │   ├── domain/                 # pure data models
│   │   │   ├── player.py           # Player, PlayerAttributes, Position
│   │   │   ├── team.py             # Team
│   │   │   ├── tactic.py           # Tactic + all the dials (enums)
│   │   │   └── match_context.py    # Weather, MatchContext
│   │   ├── engine/                 # the simulation engine
│   │   │   ├── CLAUDE.md           # THE technical reference doc for the engine
│   │   │   ├── phase.py            # Phase enum (build_up/midfield/final_third/shot)
│   │   │   ├── events.py           # EventType, MatchEvent
│   │   │   ├── summary.py          # final_score() — small utility
│   │   │   ├── probability.py      # ProbabilityModel — THE contest formula
│   │   │   ├── fatigue.py          # FatigueModel
│   │   │   ├── tactical_matchup.py # TacticalMatchup — tactic-vs-tactic modifiers
│   │   │   ├── man_marking.py      # ManMarking — man-to-man marking trade-off
│   │   │   ├── brilliance.py       # BrillianceCheck — moment of brilliance
│   │   │   ├── home_advantage.py   # HomeAdvantage
│   │   │   ├── weather_modifiers.py# WeatherModifiers
│   │   │   ├── foul.py             # FoulCheck — foul or clean tackle?
│   │   │   ├── card.py             # CardCheck — yellow/red
│   │   │   ├── injury.py           # InjuryCheck — injury
│   │   │   ├── match_situation.py  # MatchSituation (home/weather/referee, bundled)
│   │   │   ├── auto_substitution.py# AutoSubstitution — automatic subs (injury/fatigue)
│   │   │   ├── possession_chain.py # PossessionChainEngine — wires everything together
│   │   │   ├── match.py            # Match — stateful object, steppable live
│   │   │   ├── match_simulator.py  # MatchSimulator — "run it all at once" wrapper
│   │   │   └── rating/
│   │   │       ├── CLAUDE.md       # reference doc for the rating layer
│   │   │       ├── tables.py       # weights per phase/attribute — AS DATA
│   │   │       ├── calculator.py   # PhaseRatingCalculator
│   │   │       └── selector.py     # ProtagonistSelector
│   │   ├── commentary/
│   │   │   ├── CLAUDE.md           # reference doc for the commentary layer
│   │   │   ├── templates.py        # text banks — AS DATA
│   │   │   └── generator.py        # CommentaryGenerator
│   │   ├── delivery/
│   │   │   ├── CLAUDE.md           # reference doc for the API/WebSocket layer
│   │   │   ├── schemas.py          # Pydantic wire models + domain conversion
│   │   │   ├── api/
│   │   │   │   ├── matches.py      # POST /matches, WS /stream, GET /result
│   │   │   │   └── teams.py        # POST/GET /teams
│   │   │   └── services/
│   │   │       ├── match_service.py# MatchService — session lifecycle
│   │   │       ├── team_service.py # TeamService — thin wrapper over TeamRepository
│   │   │       └── pacer.py        # Pacer — the only asyncio.sleep in the codebase
│   │   ├── persistence/            # SQLite (async) — see its own CLAUDE.md
│   │   │   ├── database.py         # engine/session factory, injectable URL
│   │   │   ├── models.py           # TeamModel, PlayerModel, MatchResultModel
│   │   │   ├── repository.py + in_memory_repository.py       # MatchRepository (live)
│   │   │   ├── team_repository.py + sql_team_repository.py   # TeamRepository (durable)
│   │   │   └── match_result_repository.py + sql_match_result_repository.py
│   │   ├── generation/
│   │   │   └── team_generator.py   # TeamGenerator/PlayerGenerator — fictional content
│   │   └── main.py                 # FastAPI app factory (`uvicorn app.main:app`)
│   ├── scripts/
│   │   ├── _teams.py               # shared make_player()/build_team()
│   │   ├── simulate_demo.py        # one simple, non-interactive scenario
│   │   ├── menu.py                 # INTERACTIVE MENU — 6 scenarios, narrated live
│   │   ├── live_client.py          # watches a match over the REAL API/WebSocket
│   │   └── seed_database.py        # populates the DB with fictional teams
│   ├── .venv/                      # required for delivery/persistence (FastAPI,
│   │                                 uvicorn, httpx, sqlalchemy, aiosqlite)
│   └── tests/                      # 95 tests, all green
└── frontend/CLAUDE.md              # not started
```

---

## 3. The data model

**`PlayerAttributes`** (1-99 scale): pace, dribbling, passing, vision,
shooting, tackling, marking, strength, positioning, aggression, composure,
stamina, **flair** (drives moments of brilliance), + 3 goalkeeper
attributes (reflexes, handling, gk_positioning).

**`Team`**: `starting_xi` (11 players required), `bench`, `tactic`.

**`Tactic`**: mentality (defensive/balanced/attacking), tempo
(slow/normal/fast), pressing (low/medium/high), width (narrow/normal/wide),
defensive_line (deep/normal/high), marking_scheme (zonal/man_to_man). All
six dials now have a real mechanical effect (§5).

**`MatchContext`**: just `weather` (clear/rain/wind) for now.

---

## 4. How a duel resolves (the heart of the engine)

Every contest (ball progression, a shot...) follows the same pipeline, in
`possession_chain.py`:

1. **Team rating** (`PhaseRatingCalculator.rate`): a weighted average of
   the attributes of players eligible for this phase, weights defined in
   `rating/tables.py` (data, not hardcoded logic).
2. **Individual rating** of the selected protagonist (`ProtagonistSelector`,
   weighted random choice — favors players with good vision/positioning).
3. **Blend**: `effective = 0.7 × team_rating + 0.3 × individual_rating`
   (the `BLEND` constant in `rating/tables.py`). This is what lets an
   individually excellent player pull the team's performance up without
   completely overriding it.
4. **Moment of brilliance** (`BrillianceCheck`): an independent, rare check
   (1% to 6% chance depending on the attacking protagonist's `flair`)
   that, if it triggers, multiplies their individual rating ×1.8 for that
   one contest only. Emits a `MOMENT_OF_BRILLIANCE` event.
5. **Context modifiers**, applied as multipliers:
   - `TacticalMatchup`: the two teams' tactics compared against each other
     (e.g. high pressing penalizes the opponent's build-up; a high
     defensive line favors a fast attacker in the final phase; width
     favors wingers in FINAL_THIRD or central players in MIDFIELD).
   - `ManMarking`: man-to-man marking's trade-off (below).
   - `HomeAdvantage`: ×1.05 bonus for the home team (always the first team
     passed to `Match`).
   - `WeatherModifiers`: rain penalizes progression phases (×0.92), wind
     penalizes the shot (×0.90).
6. **Fatigue** (`FatigueModel`): every player loses fitness with each phase
   played (faster with high tempo/pressing); fitness reduces the effective
   rating down to a floor of 0.7 (never 0 — a tired player is worse, not
   useless).
7. **Final resolution** (`ProbabilityModel`): the classic logistic formula,
   with a probability floor/ceiling:

   ```
   p = 1 / (1 + e^-((attack_rating - defense_rating) / SPREAD))
   p = clamp(p, P_MIN, P_MAX)
   outcome = rng.random() < p
   ```

### Current constants (calibrated empirically, not guessed)

| Constant | Value | File |
|---|---|---|
| `SPREAD` | 60.0 | `probability.py` |
| `P_MIN` / `P_MAX` | 0.20 / 0.80 | `probability.py` |
| `BLEND` | 0.7 (team) / 0.3 (individual) | `rating/tables.py` |
| `MINUTES_PER_CHAIN` | 2 (→ 45 sequences/match) | `match.py` |
| `BONUS_MULTIPLIER` (brilliance) | ×1.8 | `brilliance.py` |
| Brilliance chance | 1% (flair=1) to 6% (flair=99) | `brilliance.py` |
| `HOME_BONUS` | ×1.05 | `home_advantage.py` |
| Rain penalty | ×0.92 (progression phases) | `weather_modifiers.py` |
| Wind penalty | ×0.90 (shot only) | `weather_modifiers.py` |
| Fatigue floor | ×0.7 | `fatigue.py` |

**⚠️ Important discovery**: a possession chain requires winning *several
sequential duels* (3 phases + the shot). Reasonable per-duel probabilities
**compound multiplicatively** and can crush the underdog at the full-match
level even though each individual duel stays "fair." The values above were
retuned after finding that a mere 15-point gap produced a 93% win rate with
the underdog winning under 1% of the time. Current result with the tuned
values: evenly matched teams ≈ 33/33/34 (win/draw/loss), realistic gap (15
pts) ≈ 57/28/15, extreme gap (40 pts) ≈ 91/8/1. Total goals per match close
to 2.5-3 for teams of similar level.

---

## 5. Width and man-marking

The last two tactic dials, long documented but never actually wired, now
have a real effect:

- **`width`**: lives in `TacticalMatchup` (no player data needed). A team
  set to WIDE gets a bonus in FINAL_THIRD (wingers/fullbacks get to
  express themselves); NARROW gets its bonus in MIDFIELD (central
  overload). Applies to whichever side is attacking **and** whichever is
  defending, based on their own setting — a team defending wide also
  covers the flank better.
- **`marking_scheme`**: lives in its own class, `ManMarking`
  (`engine/man_marking.py`), kept separate from `TacticalMatchup` —
  because it needs to know whether the attacker in front of it is a
  genuine threat (their individual rating for this phase), and
  `TacticalMatchup` has to stay a pure function with no player data.
  Man-to-man marking gives a bonus against a player who clears a quality
  threshold (75/99), but a flat penalty the rest of the time (the marker
  is glued to their man, no longer covering their zone) — a real
  trade-off, not a free bonus. Never applies to the shot phase (a
  goalkeeper facing a shot isn't "man-marking" the shooter).

**Bug (another one!) found while writing this feature's statistical test**:
the previous fix (§10, capturing `Team`'s original composition to restore
it at every match) took that snapshot **at `Team` construction time** — so
*before* a script does `home.starting_xi[9] = my_star_player`. Result:
`Match` silently overwrote that change at kickoff, and the menu's
"star striker" scenario never actually featured the star striker anymore,
with no error or warning. Fixed by making the snapshot **lazy**: it's
taken the first time a `Team` plays a match (which correctly captures any
customization done beforehand), and restored only for later matches
reusing the same object.

---

## 6. The state machine (a "possession chain")

```
RESTART → BUILD_UP → MIDFIELD → FINAL_THIRD → SHOT → GOAL / SAVE / BLOCK / OFF_TARGET
             |            |            |
          turnover     turnover     turnover  →  the other team gets the ball
```

Every "success" arrow is a duel resolved via the §4 pipeline. A turnover
at any phase ends the chain — **unless it's a foul** (§7 below), in which
case the attacking team keeps the ball. **Not implemented yet**: offside,
corners/free-kicks as their own sequences (they're on the roadmap).

---

## 7. Fouls, cards, injuries

Only triggers when the attacker **loses** a progression duel
(BUILD_UP/MIDFIELD/FINAL_THIRD) — never on the shot (a penalty is a
separate mechanic, not built yet).

1. **`FoulCheck`**: 25% of lost duels turn out to be a foul (not a clean
   tackle). Severity = tackler's aggression − ball carrier's dribbling,
   floored at 0, scaled by zone (FINAL_THIRD is more severe than BUILD_UP
   — stopping an advanced attack reads as more "cynical").
2. **Key mechanical consequence**: a foul = a free kick, **not a
   turnover** — the attacking team keeps the ball for the next sequence
   (`ChainResult.possession_retained`). This is what makes a foul genuinely
   different from a clean tackle, not just different flavor text.
3. **`CardCheck`**: `danger = severity × referee_severity`. The referee's
   severity is drawn once per match (0.7 to 1.3, in `Match.__init__`) —
   some matches are whistled strictly, others let a lot go, which is part
   of the luck pillar. A 2nd yellow card for the same player automatically
   becomes a red.
4. **`InjuryCheck`**: an independent, rare risk, on the victim of the foul
   (the fouled ball carrier) or on the tackler themselves in the case of a
   clean but committed tackle (an injury on a 100% legal challenge happens
   in real life too).
5. **Red card or injury** → the player's `available` flag becomes `False`
   (not a physical removal from the list of 11!). Why: actually removing
   them from the list would have broken the statistical tests that reuse
   the same `Team`/`Player` objects across hundreds of matches — the exact
   same kind of bug already hit with `fitness`. `available` is reset to
   `True` at the start of every new `Match`, like `fitness` and
   `yellow_cards`.

⚠️ A subtle detail if you re-read the raw events: for `FOUL`/`CARD`,
`team_id` names the team **that committed the foul/card** — whereas for
`POSSESSION_PROGRESS`/`TURNOVER`, `team_id` names the team that **was
attacking**. Two different conventions depending on event type, not a bug.

---

## 8. Narrative commentary

`app/commentary/` turns a raw `MatchEvent` into a sentence — this is what
answers the project's very first ask ("he shoots... GOAL!" rather than
unreadable JSON). Deliberately separate from the engine: the engine never
formats text, commentary never decides an outcome.

- **`templates.py`**: banks of phrases per event type (data, not code). A
  phrase is picked at random from the bank each time to avoid repetition.
- **Three event types get attribute-flavored treatment** instead of one
  flat bank: `POSSESSION_PROGRESS` (protagonist's pace/dribbling/vision),
  `SHOT` (shooter's shooting power vs composure), `FOUL` (tackler's
  aggression — "reckless"/"crunching" phrasing). In every case only if the
  winning attribute clears 70/99 — otherwise, generic phrasing. A fast
  player "explodes," a big shot "strikes it with real power," an
  aggressive tackler "flies into a reckless challenge" — nobody gets the
  flashy phrasing for an unremarkable stat.
- **`CommentaryGenerator.describe(event, roster, rng)`**: `roster` is a
  dict of `player id -> Player` (`MatchEvent`s only ever carry ids, never
  full player objects — commentary is what resolves them into names).
- **Determinism**: narrating a whole match in one pass (as `menu.py` does)
  happens *after* the engine's internal RNG has already been fully
  consumed by the simulation — so a second `random.Random(seed)` is used
  with the **same seed**, giving text that's just as reproducible without
  reusing the same instance.

`scripts/menu.py` now genuinely uses this system (it used to have its own
throwaway formatter while waiting for this module to exist).

---

## 9. Live control: `Match` — the single most important architectural piece

`Match` (in `match.py`) is a *stateful* object, not a function that runs
straight through. It exposes:

- `play_next_chain()` — advances by one possession sequence.
- `change_tactic(team, tactic)` — changes a team's tactic, effective
  **immediately** on the next sequence.
- `substitute(team, player_out, player_in)` — swaps a player, also
  effective immediately.

**Why this works with no complicated plumbing**: the engine always reads
`team.tactic` and `team.starting_xi` live off the `Team` object, never a
snapshot frozen at kickoff. So mutating those objects between two
`play_next_chain()` calls is the entire mechanism.

`MatchSimulator.simulate()` remains a simple shortcut that runs a `Match`
straight through in one go, for cases where nothing needs to change along
the way (tests, simple scripts).

**Proven by statistical test** (`tests/engine/test_match.py`): switching to
an attacking tactic at halftime measurably increases second-half goals;
bringing on a much better striker does too. Not just accepted as input and
ignored.

---

## 10. Automatic substitutions

`AutoSubstitution` (`engine/auto_substitution.py`) runs after every
sequence, for both teams. Two triggers, kept clearly distinct from
`Match.substitute()` (the manual control from §9, with no limit or bench
bookkeeping):

1. **Injury**: as soon as a player is injured, immediately tries to bring
   on a replacement of the **same position** from the bench.
2. **Tiredness**: when a starter's fitness drops below 0.72 (calibrated
   empirically — even the most heavily used player rarely drops below
   ~0.53 over 90 minutes at the current fatigue rate), the most tired
   starter is replaced if a same-position player is available on the
   bench. Only one player per check, not the whole team at once.

**Important rule**: a red card **never** triggers an automatic
substitution (in real football, you don't replace a sent-off player — the
team plays with 10 men). Proven by test.

Both respect a limit of 5 substitutions per team (`Team.substitutions_used`),
managed only by `AutoSubstitution` (not by `Match.substitute()`, which
remains a low-level tool with no limit).

⚠️ For this to work, test/demo teams needed a real bench (`_teams.py`,
`factories.py` now generate 5 substitutes per team) — otherwise
`AutoSubstitution` never has anyone to bring on.

**Bug (yet another one) hit and fixed**: substituting a player really
mutates `starting_xi`/`bench` — but since the statistical tests reuse the
same `Team` objects across hundreds of matches, a substitution made in one
match "contaminated" the next (different squad composition → different
results → broken reproducibility tests). Fix: `Team` now captures a copy
of its original composition, which `Match` restores at the kickoff of
**every** new match — the same principle as resetting `fitness`, applied
this time to the team's own composition (see §5 for the follow-up bug this
same fix caused, and how it was corrected).

---

## 11. How to test it yourself

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # first time only
pip install -e ".[dev]"                             # first time only

pytest -q                         # the 95 tests (unit + statistical + API)
python scripts/simulate_demo.py   # one fixed scenario, raw event feed
python scripts/menu.py            # INTERACTIVE MENU, 6 scenarios:
python scripts/live_client.py     # watch a match over the REAL API/WebSocket
                                   # (real-time paced, ~30s — see §13)
uvicorn app.main:app --reload     # run the live API yourself (§13)
```

(Everything except `tests/delivery/` also runs fine with plain system
`python3`/`pytest` — no venv needed — since FastAPI/uvicorn/httpx are only
required for the delivery layer. Using the venv for everything is simplest
and is what's assumed above.)

Menu scenarios:
1. Evenly matched teams (60 vs 60)
2. Strong vs weak, contrasting tactics (80 vs 45)
3. Star striker carrying a mediocre team
4. High defensive line vs pacey wingers
5. Same level, but in the rain
6. **Live control**: tactic switch + substitution at halftime, to see the
   immediate effect

To build your own scenario: copy a `_scenario_...` function in `menu.py`,
adjust `overall`, the `Tactic(...)`, or replace a specific player via
`make_player(..., shooting=95, pace=90, ...)`.

---

## 12. What's left to do (short term)

- Extend "attribute-flavored" commentary (§8) to the remaining flat-bank
  event types (GOAL, CARD, INJURY...) — POSSESSION_PROGRESS, SHOT, and FOUL
  already have it
- Offside, corners/free-kicks as their own sequences (for now a foul just
  restarts a normal chain)
- A standalone player repository / free-agent pool, once transfers exist
  (Phase 7) — right now a player only exists as part of a team
- Migrations (Alembic) — schema still moves too fast to be worth it
- After that: frontend (Phase 4)... see the full roadmap in `README.md`

---

## 13. Live delivery: API + WebSocket (Phase 2)

The match engine is now reachable over HTTP/WebSocket, not just the
terminal. `app/main.py` is the FastAPI app factory (`uvicorn app.main:app`).

- **`POST /matches`** — body has `team_a`/`team_b` (full squads, wire
  format in `delivery/schemas.py`), optional `seed`, optional `weather`.
  Returns `{"match_id": "..."}` and starts the simulation **immediately**,
  server-side, in a background task — it does not wait for anyone to
  connect.
- **`GET /matches/{match_id}/stream`** (WebSocket) — sends the full backlog
  first (fast, no delay), then keeps polling and forwarding new events as
  the simulation produces them. Closes with code `4004` if the match
  doesn't exist. Every message includes the rendered commentary line, not
  just the raw event.
- **One simulation per match, however many viewers.** `MatchService` runs
  `Match.play_next_chain()` in a loop inside a single background task per
  match, appending each chain's events (with commentary) to an in-memory
  `MatchRepository`. All WebSocket connections for that `match_id` just
  read from the same growing list — proven by test (`test_two_viewers_of_
  the_same_match_see_the_same_events`).
- **`Pacer`** is the only place `asyncio.sleep` happens (`delivery/services/
  pacer.py`), so the engine itself stays a plain, real-time-agnostic
  function. Its pace (real seconds per game-minute) is a constructor
  argument, which is what let tests inject a near-zero pace instead of
  waiting out a real ~27-second match.

**New venv required**: FastAPI/uvicorn/httpx aren't available system-wide
like pytest was — `backend/.venv` now exists specifically for this
(`pip install -e ".[dev]"`).

**Non-obvious bugs hit while building this:**

1. `MatchService._run()` originally read events from the `ChainResult` that
   `play_next_chain()` returns — but `KICKOFF` (added in `Match.__init__`,
   before any chain runs) and `FULL_TIME` (appended inside
   `play_next_chain()` itself, separately from the `ChainResult`) both live
   on `match.events`, Match's own running log, not in that per-chain
   result. The fix reads `match.events[sent:]` each iteration instead —
   otherwise every WebSocket stream would silently start on the first
   chain's events and end right after the last goal/shot, never actually
   announcing kickoff or full time.
2. **FastAPI's `TestClient` has to wrap the *entire* test**, not just the
   WebSocket part. `MatchService.start_match()` schedules the simulation
   via `asyncio.create_task()`; that only keeps running if a single
   persistent event loop backs the whole test, which `with TestClient(app)
   as client:` provides. Doing `client.post(...)` outside that `with` block
   tears down the loop hosting the background task the instant the request
   finishes — the match then never progresses, and any WebSocket polling
   for new events just hangs forever (this is exactly what happened on the
   first attempt, until the test was rewritten around one `with` block for
   the whole flow).

---

## 14. Persistence (Phase 3)

SQLite, async, via SQLAlchemy + `aiosqlite` — zero setup (a file, no
server to run), and upgradeable to PostgreSQL later without touching
services or routes, since everything goes through repository interfaces
(`app/persistence/`, one `CLAUDE.md` of its own now).

**Two repositories with deliberately different lifetimes** — don't merge them:

- **`MatchRepository`** (already existed, §13) — the *live* event log for
  a match currently streaming. Stays in-memory on purpose: nobody needs a
  currently-running match's blow-by-blow to survive a restart, and writing
  every event to disk in real time would be wasted I/O.
- **`MatchResultRepository`** (new) — the *durable* record of a **finished**
  match: final score, both teams' ids/names, seed, and the full
  commentary-annotated event log, written once when `MatchService` sees
  `match.finished`. This is what makes `GET /matches/{id}/result` survive a
  server restart, unlike `/stream`.

**`TeamRepository`** persists a `Team`'s full roster (`starting_xi` +
`bench`) and `Tactic`. No standalone player repository yet — a player only
exists as part of a team (no free agents/transfers until Phase 7), so
`PlayerModel` is just a child table of `TeamModel`. New routes:
`POST /teams`, `GET /teams/{id}`, `GET /teams`.

**Fictional content generation** (`app/generation/team_generator.py`):
this project uses no real-world player data, so `TeamGenerator`/
`PlayerGenerator` procedurally invent players — name pools plus attributes
rolled from a Gaussian centered on a requested "quality" tier, clamped to
1-99. Deterministic given a seeded `random.Random`, including for **ids**:
`uuid.uuid4()` would have silently broken that determinism (it reads
`os.urandom`, not the seeded generator), so ids are derived from the same
RNG instead (`rng.getrandbits(64)`, hex-formatted). `scripts/seed_database.py`
populates the database with a handful of generated teams.

**Testability**: `create_engine_and_session_factory(database_url)` takes
the URL as an argument rather than reading a hardcoded global — tests
always pass `sqlite+aiosqlite:///:memory:`, so nothing leaks between test
runs (the same fix, for the same reason, as `Team`'s original-composition
snapshot in §5/§10). In-memory SQLite specifically needs `StaticPool` to
keep one connection (and therefore one database) alive across the multiple
sessions a single test can open — otherwise every new session would see a
brand new, empty `:memory:` database. No `pytest-asyncio` dependency
either: repository tests just wrap each async call in a plain
`asyncio.run(...)` from an ordinary sync test function.

---

## 15. Where to find precise technical detail

This file is a summary to help you remember the big picture. For exact
detail meant for coding (full formulas, weight tables, event taxonomy):

- [`CLAUDE.md`](../CLAUDE.md) — overall vision, conventions
- [`backend/CLAUDE.md`](../backend/CLAUDE.md) — backend code conventions
- [`backend/app/engine/CLAUDE.md`](../backend/app/engine/CLAUDE.md) — **the engine's reference doc**
- [`backend/app/commentary/CLAUDE.md`](../backend/app/commentary/CLAUDE.md) — the commentary layer
- [`backend/app/engine/rating/CLAUDE.md`](../backend/app/engine/rating/CLAUDE.md) — the stats → ratings layer
- [`backend/app/delivery/CLAUDE.md`](../backend/app/delivery/CLAUDE.md) — the API/WebSocket layer
- [`backend/app/persistence/CLAUDE.md`](../backend/app/persistence/CLAUDE.md) — the persistence layer
- [`README.md`](../README.md) — full roadmap (10 phases)
