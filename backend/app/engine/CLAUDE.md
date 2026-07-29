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

- Foul severity is a contest between the tackler's Aggression and the ball
  carrier's Dribbling, modified by zone (fouls in the defensive third that
  stop a promising attack are treated as more severe).
- Card sub-roll: severity + tackler's Aggression/Composure + a per-match
  "referee strictness" modifier (a single random value drawn once per match
  from a reasonable range, so some matches are just card-happy — this is
  also part of the variance pillar) → no card / yellow / red. A second
  yellow becomes a red and removes the player.
- Injury: a small independent probability check on fouls and on
  high-Aggression duels generally. An injured player must be substituted (or
  the team plays a man down if no substitutions remain) — feeds §8.

## 7. Set pieces (v1, lightweight)

Corners and free-kicks in shooting range are treated as a FINAL_THIRD ->
SHOT sequence with a bonus weighting towards aerial duels (Strength) for
corners specifically. Throw-ins and deep free-kicks just restart a normal
BUILD_UP/MIDFIELD chain. Don't over-build this in v1 — it's a restart flavor,
not a separate simulation system.

## 8. Substitutions

MVP: AI-driven, no human-in-the-loop mid-match decisions yet.

- Tiredness-triggered: once a player's fatigue factor crosses a threshold
  (roughly minute 60-75 depending on Stamina), sub in a bench player of the
  same position if one is available.
- Injury-triggered: immediate, same-position bench player if available.
- Tactical subs (chasing/protecting a scoreline) are a future extension, not
  MVP.

## 9. Tuning constants

`SPREAD`, `P_MIN`/`P_MAX`, fatigue decay rates, and all tactical-matchup
modifier values are constants that cannot be correctly guessed up front —
they need to be tuned against the statistical tests described in
`backend/CLAUDE.md`. Keep them centralized (a single `constants.py` or
similar) rather than scattered as magic numbers through the phase logic, so
balancing passes are tractable.

## 10. MatchEvent taxonomy

| Event type | Key payload |
|---|---|
| KICKOFF | team with first possession |
| POSSESSION_PROGRESS | phase (build_up/midfield/final_third), team, key player(s) |
| CHANCE_CREATED | team, creator player, zone |
| SHOT | shooter, assist (optional), shot quality tier |
| GOAL | scorer, assist (optional), current score |
| SAVE | goalkeeper, shooter, rebound: bool |
| BLOCK | blocker, shooter |
| OFF_TARGET | shooter |
| CORNER / THROW_IN / GOAL_KICK / FREE_KICK | team, zone |
| OFFSIDE | player |
| FOUL | fouling player, fouled player, zone |
| CARD | player, yellow/red, reason (foul reference) |
| INJURY | player |
| SUBSTITUTION | player_out, player_in, reason (tired/injury) |
| HALF_TIME / FULL_TIME | current score, aggregate stats |

Every event carries: `minute`, `team` (nullable for neutral events), and a
list of `players` involved. Commentary text is **not** stored on the event
itself — see `app/commentary/CLAUDE.md` for why that's a separate layer.

## Explicitly out of scope for MVP

- Player heat-maps / positional coordinates.
- xG-style advanced stats display.
- Mid-match human tactical changes streamed back into a running simulation.
- Morale, weather, pitch condition, referee personality profiles beyond the
  single per-match strictness modifier in §6.
- Anything related to persistence — the engine just yields events; what
  happens to them after is `delivery/`'s problem.
