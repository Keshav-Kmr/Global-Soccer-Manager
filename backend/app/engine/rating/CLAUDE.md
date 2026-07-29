# Rating (stats -> phase ratings)

This is the missing link between `app/domain` (raw player attributes) and the
contest formula in `engine/CLAUDE.md` §4: **how do 11 players, a formation,
and a tactic collapse into the one attacker/defender number a phase contest
actually compares?** Getting this right — and structured so it can evolve —
matters more than almost anything else in the engine, because every future
feature (chemistry, morale, home advantage, squad depth mattering) plugs in
here rather than into the phase state machine or the probability formula.

Two distinct responsibilities, two distinct classes. Don't merge them — they
change for different reasons and at different rates.

## 1. `PhaseRatingCalculator` — team-level aggregate

Answers: "how good is this team, right now, at this specific phase?" This is
what makes squad depth matter (a weak bench player forced on by injury drags
the rating down) and is the number that should feel like "team quality."

```python
class PhaseRatingCalculator:
    """Aggregates eligible players' attributes into one phase rating,
    driven entirely by data tables — never hardcode which attribute
    matters for which phase in branching logic."""

    def rate(self, phase: Phase, players: list[Player], weights: PhaseWeights) -> float:
        ...
```

- **Eligible players** for a phase come from position codes, via a small
  mapping table (data, not branching code), e.g.:

  ```python
  PHASE_ELIGIBLE_POSITIONS = {
      Phase.BUILD_UP:     {"attack": ["CB", "DM", "GK"], "defense": ["ST", "AM"]},
      Phase.MIDFIELD:     {"attack": ["DM", "CM", "AM"], "defense": ["CM", "DM"]},
      Phase.FINAL_THIRD:  {"attack": ["AM", "W", "ST"],  "defense": ["CB", "FB"]},
      Phase.SHOT:         {"attack": ["ST", "AM", "W"],  "defense": ["GK"]},
  }
  ```

- **Attribute weights** per phase are a separate data table (see §3). The
  calculator does a weighted average across eligible players, weighted
  again by each player's fatigue-adjusted availability — it never needs an
  `if phase == BUILD_UP: use passing` branch anywhere.

## 2. `ProtagonistSelector` — who the match is actually about

Answers: "which specific player do we name in this event?" This exists
purely for the individual-attribute nuance and for commentary (see
`app/commentary/CLAUDE.md`) — matches should be *about* Dubois or Martins,
not an anonymous team blob.

```python
class ProtagonistSelector:
    """Weighted-random pick of the player(s) who are 'on the ball' for a
    phase. Must consume the match's shared random.Random instance."""

    def select(self, phase: Phase, players: list[Player], rng: random.Random) -> Player:
        ...
```

Selection weight = eligible-position weight x an "involvement" attribute
relevant to wanting the ball (e.g. Positioning/Vision for attack,
Positioning/Aggression for defense) — again driven by the same kind of data
table as §3, not bespoke logic per phase.

## 3. Combining them into the effective rating

```
team_rating   = PhaseRatingCalculator.rate(phase, eligible_players, weights)
protagonist   = ProtagonistSelector.select(phase, eligible_players, rng)
individual    = protagonist's own weighted attribute score for this phase

effective_rating = BLEND * team_rating + (1 - BLEND) * individual
```

`BLEND` (e.g. ~0.7) is a tuning constant, not a hardcoded assumption — it's
what controls how much a single "have a great game" star player can carry a
weaker team, versus how much squad-wide quality dominates. This is the exact
same value feeding into `effective_attacker`/`effective_defender` in the
contest formula (`engine/CLAUDE.md` §4) — that section's "base_attribute"
*is* this `effective_rating`, not a single player's raw stat in isolation.

## 4. Weight tables live as data, not code

`PHASE_ATTACK_WEIGHTS`, `PHASE_DEFENSE_WEIGHTS`, `PHASE_ELIGIBLE_POSITIONS`,
and `BLEND` all belong in one place (e.g. `engine/rating/tables.py` or a
loaded config file — a plain Python module of dicts/constants is enough for
v1, no need for YAML/JSON tooling yet). This is the single most important
extensibility decision in the whole engine:

- **Rebalancing** (a phase feels too pace-dominated) = edit a number in a
  table, run the statistical tests from `backend/CLAUDE.md`, done. No touching
  `PhaseRatingCalculator`, no touching the phase state machine.
- **Adding a new attribute** (e.g. a future "Leadership" attribute) = add it
  to the relevant weight rows. The calculator's weighted-average code never
  changes.
- **Adding a new phase** later (e.g. extra time, penalty shootouts) = add
  entries to these tables and a new `Phase` enum value; `PhaseRatingCalculator`
  and `ProtagonistSelector` need zero changes to support it.

## 5. Deliberate extension points (not built yet)

Called out explicitly so a future contributor knows where to add these
without having to redesign the rating layer:

- **Context modifiers** (morale, home advantage, rivalry, weather): the
  natural seam is a `modifiers: list[RatingModifier]` parameter on
  `PhaseRatingCalculator.rate()`, applied multiplicatively after the weighted
  average. Don't add this now — there's nothing to modify yet — but don't
  design `rate()`'s signature in a way that would make bolting this on later
  awkward either.
- **Chemistry between specific players** (e.g. two wingers who've played
  together for seasons): would plug in as an additional multiplier on the
  `individual` term in §3, keyed on which players are actually selected as
  protagonists in the same phase. Future work, not MVP.
- **A smarter/ML-based rating model**: because `PhaseRatingCalculator` is a
  class with a narrow `rate()` interface, an entirely different
  implementation could be swapped in later (strategy pattern) without
  touching `ProbabilityModel` or the phase state machine, as long as it
  still returns a single comparable float.

## Testing

This layer is pure arithmetic over data tables and is the cheapest place in
the whole engine to get exhaustive unit test coverage: given a fixed set of
player attributes and a fixed weight table, the expected `rate()` output is
an exact, computable number — assert it precisely, not just "in some range"
(save the statistical/range-based tests for the probability model and full
match simulations, per `backend/CLAUDE.md`).
