# Match Engine

The core of the whole project. This module simulates one football match and
produces an ordered stream of `MatchEvent` objects. It is a pure, synchronous,
deterministic component: it knows nothing about WebSockets, real time, or
pacing (see `app/delivery/CLAUDE.md` for how the output is streamed live).

```python
def simulate_match(team_a: Team, team_b: Team, seed: int) -> Iterator[MatchEvent]:
    ...
```

Calling this twice with the same arguments must yield identical events, in
identical order. All randomness goes through a single `random.Random(seed)`
instance created at the top of `simulate_match` and threaded through every
function it calls — never use the global `random` module.

Per the class-based convention in `backend/CLAUDE.md`, `simulate_match` is a
thin entry point delegating to classes with single responsibilities, e.g.
`MatchSimulator` (owns the overall loop and match state), `PossessionChainEngine`
(runs one chain's phase transitions), `ProbabilityModel` (the contest formula,
§4), `TacticalMatchup` (§2), `FatigueModel` (§3), and `PhaseRatingCalculator` /
`ProtagonistSelector` (`engine/rating/CLAUDE.md` — how player attributes turn
into the ratings the contest formula compares). Each gets its own file under
`engine/`, grouped into subfolders when a concern is cohesive enough to
deserve one (as `rating/` does), with a docstring explaining its role. Don't
collapse them into one large module.

## 1. Domain model

### Player attributes

Scale: **1-99** (familiar FM-style range, gives enough granularity for
noticeable differences without implying false precision).

Outfield:

| Attribute     | Affects |
|---------------|---------|
| Pace          | Progression speed, counter-attacks, beating a defender in behind |
| Dribbling     | Beating a defender 1v1, entering the box under pressure |
| Passing       | Progressing the ball through build-up/midfield, chance creation |
| Vision        | Creating high-quality chances (key passes), unlocking deep defenses |
| Shooting      | Shot quality/finishing once a shot is taken |
| Tackling      | Regaining possession in a duel, last-ditch defending |
| Marking       | Positional defending, preventing box entry, following a runner |
| Strength      | Physical duels, holding off pressure |
| Positioning   | Being available for progression; for defenders, being goal-side |
| Aggression    | More duels contested/won, but raises foul & card risk |
| Composure     | Lowers foul/card risk under pressure, improves shot quality when rushed |
| Stamina       | Rate of attribute decay over the 90 minutes |
| Flair         | Drives BrillianceCheck (§4.1): a rare, independent chance of a standout individual moment |

Goalkeeper-specific (replace outfield shot-relevant attributes):

| Attribute   | Affects |
|-------------|---------|
| Reflexes    | Shot-stopping on well-struck/close-range shots |
| Handling    | Whether a save is held (no rebound) or spilled (rebound chance) |
| GK Positioning | Reduces effective shot quality by narrowing the angle |

v1 does **not** model kicking/distribution, aerial ability, or communication
— add only if a concrete mechanic needs them.

### Team model

- **Formation**: an ordered list of slots, each with a position code (GK, CB,
  FB, DM, CM, AM, W, ST) and the player assigned to it. Formation shapes which
  players are "available" as options in each phase (e.g. wingers are the
  primary width-phase actors; a DM is a primary build-up phase actor).
- **Tactic**: a set of independent dials chosen by the manager. Each one
  changes match flow, not just a flat modifier on an existing shape:

  | Dial | Values | Structural effect |
  |------|--------|--------------------|
  | Mentality | Defensive / Balanced / Attacking | Shifts how many chain attempts are committed forward vs how exposed the team is to opponent counters. Attacking = more chain attempts & better final-third ratings, worse recovery rating on opponent turnovers. |
  | Tempo | Slow / Normal / Fast | Slow = more progression sub-steps per chain (more control, more attrition/foul opportunities); Fast = fewer steps, higher variance, better for counters, worse ball retention. |
  | Pressing | Low / Medium / High | Directly debuffs the *opponent's* effective Passing/Composure during their build-up/midfield phases. High pressing drains the pressing team's stamina faster. |
  | Width | Narrow / Normal / Wide | Shifts which player archetypes (wingers/fullbacks vs central players) get weighted into final-third phases. |
  | Defensive line | Deep / Normal / High | High line increases interception rate in midfield but raises the chance of a pacey attacker beating it for a clear chance (and raises offside frequency). |
  | Marking scheme | Zonal / Man-to-man | Man-to-man can neutralize a specific high-quality opponent (direct attribute contest against their marker) at the cost of weakening that marker's zone elsewhere. |

## 2. Tactical matchup layer

This is what makes tactics a real pillar instead of a coefficient. Before
individual player duels are resolved, the two teams' tactic dials are
compared and produce **asymmetric modifiers** applied to the effective
attributes used in that phase. Examples (illustrative — exact numbers are
tuning constants, see §9):

- High Press vs a team with low Tempo/low Passing: build-up phase gets an
  extra penalty (the low-tempo team can't play through the press).
- High Defensive Line vs an opponent with high-Pace attackers: final-third
  phase attacker rating gets a bonus (through balls in behind), but the
  offside sub-check (§6) is also rolled more often.
- Wide vs Narrow: the wide team's wingers/fullbacks get a rating bonus in
  final-third phases; the narrow team's central players get a bonus in
  midfield phases instead.
- Man-marking vs a specific star player: that player's attribute edge in
  direct duels against their marker is reduced, but the marker contributes
  less to duels elsewhere on the pitch (a real trade-off, not a free
  counter).

Implementation shape: a `TacticalMatchup` function takes both teams' tactics
and the current phase, and returns a modifier pair `(mod_a, mod_b)` applied
multiplicatively to the effective ratings before the contest formula (§4)
runs.

## 3. Fatigue

Effective attribute = base attribute x tactic modifiers x fatigue factor.

Stamina depletes per phase a player participates in; the depletion rate is
itself increased by high Tempo and high Pressing (both dials cost more
energy). `fatigue_factor` degrades smoothly from 1.0 towards a floor
(e.g. ~0.7) as stamina depletes — never to zero; a tired player is worse, not
useless.

## 4. Contest resolution formula

Every duel in the engine — progression, chance creation, tackles, shots —
resolves through the same primitive:

```
effective_attacker = phase_rating_attacker * tactic_mod_attacker * fatigue_attacker
effective_defender = phase_rating_defender * tactic_mod_defender * fatigue_defender

p = 1 / (1 + e^(-(effective_attacker - effective_defender) / SPREAD))
p = clamp(p, P_MIN, P_MAX)   # e.g. P_MIN=0.10, P_MAX=0.90

outcome = rng.random() < p
```

`phase_rating_*` is **not** a single player's raw attribute — it's the
output of `PhaseRatingCalculator`/`ProtagonistSelector`, which blend a
team-wide aggregate with the selected protagonist's individual attributes.
See `engine/rating/CLAUDE.md` for exactly how that number is built and why
it's structured as data-driven weight tables rather than branching logic —
that's what keeps rebalancing and adding attributes/phases later cheap.

- `SPREAD` controls how much a rating gap matters and can be tuned per phase
  type (e.g. shots might be more variance-prone than build-up progression).
- Clamping to `[P_MIN, P_MAX]` is where **structural luck** lives: no team is
  ever a guaranteed winner or loser of a duel.
- The `rng.random() < p` roll is where **stochastic luck** lives: even an
  80/20 favorite loses the duel 1 time in 5, and across a season that's
  exactly the kind of upset an open-source football sim should be able to
  produce.

## 4.1 Moments of brilliance

The team/individual blend in §4 (and `engine/rating/CLAUDE.md` §3) is a
smooth, continuous statistical tilt — a better player does a *bit* better,
consistently. That's not the same thing as "a flash of genius," which is a
rare, discrete spike, not a permanent tilt. `BrillianceCheck`
(`engine/brilliance.py`) is a separate, independent roll per contest: scaled
by the attacking protagonist's Flair, capped low (a few percent at most —
if it stops being rare it stops reading as brilliance), and when it hits, it
multiplies that player's individual contribution for that one contest only
before the blend/matchup/fatigue chain runs. This was exactly the kind of
addition `engine/rating/CLAUDE.md` §5 flagged as a future extension point —
it didn't require touching `PhaseRatingCalculator`, `ProbabilityModel`, or
the phase state machine.

## 4.2 Match context: home advantage & weather

Two more multipliers applied alongside the tactical-matchup modifier in §2,
but conceptually distinct from it because they aren't about either team's
choices:

- **Home advantage** (`engine/home_advantage.py`): a small flat bonus
  (v1: a single constant) for whichever team is playing at home — currently
  just "whichever team is passed first to `Match`," not a separate flag.
- **Weather** (`engine/weather_modifiers.py`, `domain/match_context.py`):
  match-wide conditions — Rain penalizes the progression phases (harder
  passing/dribbling on a slick pitch); Wind penalizes the shot phase only.
  Applies identically regardless of which team is attacking, unlike
  `TacticalMatchup`, which is asymmetric between the two teams' tactics.

Both are deliberately simple starting points (flat constants), not a full
simulation of crowd noise or rain intensity — plausible refinements of
these same two classes later, not new systems.

## 5. Match loop / possession chain state machine

```
RESTART (kickoff / goal kick / throw-in / free-kick / corner)
   |
   v
BUILD_UP (defensive third) --turnover--> opponent's BUILD_UP (counter context)
   |success                              (fast counters may skip a phase if
   v                                      Tempo is Fast and turnover happened
MIDFIELD (middle third) --turnover--> opponent's BUILD_UP               high up the pitch)
   |success
   v
FINAL_THIRD / CHANCE_CREATION --turnover--> opponent's BUILD_UP
   |success (box entry)     \--offside--> RESTART (free kick)
   v                          \--foul--> FOUL_EVENT
SHOT
   |--> GOAL --> RESTART (kickoff, other team)
   |--> SAVED (held) --> RESTART (goal kick)
   |--> SAVED (parried/rebound) --> possible follow-up SHOT (rebound scramble)
   |--> BLOCKED --> RESTART (corner)
   |--> OFF_TARGET / POST --> RESTART (goal kick)

FOUL_EVENT can occur inside BUILD_UP, MIDFIELD, or FINAL_THIRD; resolves to a
free kick RESTART (direct or indirect depending on zone) and a card sub-check.
INJURY_EVENT can trigger off any foul or high-Aggression duel; feeds into
substitution logic (§8).
```

Each arrow that isn't an instant transition is itself a contest resolved via
§4, using the phase-appropriate attributes (e.g. BUILD_UP uses
Passing/Composure vs Pressing-modified Tackling/Marking; FINAL_THIRD uses
Dribbling/Vision vs Marking/Positioning; SHOT uses Shooting/Composure vs
GK Reflexes/Handling/Positioning, further reduced by defensive pressure at
the moment of the shot).

## 6. Fouls, cards, injuries

Rolled only when the attacker **loses** a progression phase (BUILD_UP,
MIDFIELD, FINAL_THIRD) — a phase the attacker wins is clean possession
play, not a physical duel worth checking. SHOT is excluded (a foul that
stops a shot is a penalty, a distinct future mechanic, §7).

- **FoulCheck** (`engine/foul.py`): 25% (`FOUL_CHANCE`) of lost duels turn
  out to be a foul rather than a clean tackle. Severity = the tackler's
  Aggression minus the ball carrier's Dribbling, floored at 0, scaled by a
  zone multiplier — fouls in FINAL_THIRD read as more cynical/severe than
  ones in BUILD_UP.
- **Mechanically, a foul is a free kick, not a turnover**: the attacking
  team keeps the ball for the next chain instead of conceding possession
  (`ChainResult.possession_retained`, honored by `Match.play_next_chain()`).
  A clean tackle still ends the chain with a normal TURNOVER, as before.
- **CardCheck** (`engine/card.py`): `danger = severity * referee_strictness`
  drives yellow/red probabilities. Referee strictness is a single value
  drawn once per match (`Match.__init__`, range 0.7–1.3), so some matches
  are just card-happy and others let a lot go — deliberately part of the
  variance pillar (root CLAUDE.md), not noise to average away. A second
  yellow for the same player converts that event into a red.
- A CARD event's `team_id` is the **carded player's own team** — note this
  differs from POSSESSION_PROGRESS/TURNOVER, where `team_id` is the
  attacking team. FOUL events follow the same "whose event is this about"
  convention as CARD (`team_id` = the team that committed the foul), so a
  FOUL and the CARD that follows it always share the same `team_id`.
- **InjuryCheck** (`engine/injury.py`): a small independent risk, checked
  on whichever player was actually exposed to the physical duel — the
  fouled ball carrier if it was a foul, or the tackler themselves on a hard
  but clean challenge. Not derived from card severity: a legal, hard-fought
  tackle can injure just as a cynical foul can.
- **A red card or an injury sets `Player.available = False`** — excluded
  from `eligible_players()` (`engine/rating/tables.py`) for the rest of the
  match, so the team plays short-handed. This is deliberately a flag, not a
  physical removal from `Team.starting_xi`: removing the player from the
  list permanently would leak across independent `Match()` calls that
  happen to share the same `Team`/`Player` objects (exactly the same class
  of bug fixed earlier for `fitness` — see `Match.__init__`, which resets
  `fitness`, `yellow_cards`, and `available` together at kickoff). A human
  driving the match live can bring on a replacement via `Match.substitute()`
  (§11); nothing does this automatically yet (§8).

## 7. Set pieces (v1, lightweight)

Corners and free-kicks in shooting range are treated as a FINAL_THIRD ->
SHOT sequence with a bonus weighting towards aerial duels (Strength) for
corners specifically. Throw-ins and deep free-kicks just restart a normal
BUILD_UP/MIDFIELD chain. Don't over-build this in v1 — it's a restart flavor,
not a separate simulation system.

## 8. Substitutions

Live, human-in-the-loop substitutions exist now via `Match.substitute()`
(§11) — a caller can swap a starting player for any other `Player` between
possession chains and it takes effect on the very next one. What's still
missing is the *automatic* side:

- Tiredness-triggered: once a player's fatigue factor crosses a threshold
  (roughly minute 60-75 depending on Stamina), sub in a bench player of the
  same position if one is available.
- Injury-triggered: immediate, same-position bench player if available.

`Match.substitute()` also doesn't manage bench bookkeeping (removing the
incoming player from `Team.bench`, enforcing a substitution limit) — that's
squad-management scope (README roadmap Phase 5), not the match engine's.

## 9. Tuning constants

`SPREAD`, `P_MIN`/`P_MAX`, fatigue decay rates, and all tactical-matchup
modifier values are constants that cannot be correctly guessed up front —
they need to be tuned against the statistical tests described in
`backend/CLAUDE.md`. Keep them centralized (a single `constants.py` or
similar) rather than scattered as magic numbers through the phase logic, so
balancing passes are tractable.

## 10. MatchEvent taxonomy

Implemented today:

| Event type | Key payload |
|---|---|
| KICKOFF | team with first possession |
| POSSESSION_PROGRESS | phase (build_up/midfield/final_third), team, key player |
| TURNOVER | phase, team that lost possession, player |
| MOMENT_OF_BRILLIANCE | team, player (§4.1) |
| FOUL | team that fouled, [tackler, ball_carrier], phase (§6) |
| CARD | fouling player's team, player, color: yellow/red (§6) |
| INJURY | injured player's team, player (§6) |
| SHOT | shooter |
| GOAL | scorer |
| SAVE | shooter, goalkeeper |
| BLOCK | shooter |
| OFF_TARGET | shooter |
| TACTIC_CHANGE | team, new mentality/pressing (§11) |
| SUBSTITUTION | player_out, player_in (§11) |
| FULL_TIME | — |

Planned, not yet implemented (see README roadmap):

| Event type | Key payload |
|---|---|
| CHANCE_CREATED | team, creator player, zone |
| CORNER / THROW_IN / GOAL_KICK / FREE_KICK | team, zone |
| OFFSIDE | player |
| HALF_TIME | current score, aggregate stats |

Every event carries: `minute`, `team` (nullable for neutral events), and a
list of `players` involved. Commentary text is **not** stored on the event
itself — see `app/commentary/CLAUDE.md` for why that's a separate layer.

## 11. Live match control: tactic changes and substitutions mid-match

`Match` (`engine/match.py`) is the stateful primitive behind
`MatchSimulator.simulate()` — it exposes `play_next_chain()` to advance one
possession chain at a time, plus `change_tactic(team, tactic)` and
`substitute(team, player_out, player_in)` to be called *between* chains.
Both take effect immediately, with no special plumbing: `PossessionChainEngine`
always reads `team.tactic` and `team.starting_xi` live off the `Team`
object it's given, never a snapshot taken at kickoff, so mutating those
objects between `play_next_chain()` calls is the entire mechanism. This is
what makes tactics genuinely central rather than a match-start-only
setting — see `tests/engine/test_match.py` for statistical proof that a
mid-match tactical switch and a mid-match substitution each measurably
change what happens afterward.

`MatchSimulator.simulate()` still exists as a thin convenience wrapper
(`Match(...).play_to_completion()`) for the common case where nothing needs
to change mid-match — existing callers are unaffected.

## Explicitly out of scope for MVP

- Player heat-maps / positional coordinates.
- xG-style advanced stats display.
- Morale, pitch condition, referee personality profiles beyond the single
  per-match strictness modifier in §6.
- AI-driven automatic substitutions (tiredness/injury-triggered) — the
  mechanism exists (§8, §11) but nothing calls it automatically yet.
- Anything related to persistence — the engine just yields events; what
  happens to them after is `delivery/`'s problem.
