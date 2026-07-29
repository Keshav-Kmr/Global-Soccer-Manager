# Commentary

Turns a `MatchEvent` (structured data from `app/engine`) into a narrative
text line. This is a deliberately separate layer from the engine: the engine
must never format strings, and the commentary layer must never decide game
outcomes. That separation is what makes both sides independently testable
and lets commentary style evolve (more variety, later localization, maybe a
future LLM-based flavor pass) without ever touching simulation logic.

```python
class CommentaryGenerator:
    def describe(self, event: MatchEvent, roster: dict[str, Player], rng: random.Random) -> str:
        ...
```

Implemented in `generator.py`. `roster` (player id -> `Player`) is what lets
templates reference names/attributes — `MatchEvent` deliberately only
carries ids (engine/CLAUDE.md §10), so this is the layer that resolves
them; callers build it from `team.starting_xi`/`team.bench` for both teams.

`rng` should be the *same* `random.Random` instance used by the engine for
that match if narrating live, or a clearly seeded child of it — in
practice, narrating a whole finished event list in one pass (as
`scripts/menu.py` does) happens after the engine's own RNG has already
been fully consumed, so the actual pattern is `random.Random(match.seed)`:
a fresh instance seeded the same way, which is exactly what "a clearly
seeded child" means here. Either way, the full match — commentary included
— stays reproducible from a single seed.

## Template bank approach

Each `MatchEvent` type has a bank of multiple template variants (`templates.py`),
one chosen via the match's RNG per event to avoid repetitive-sounding
matches. v1 selects uniformly (`rng.choice`) — genuinely weighting specific
variants higher is a plausible refinement once we have opinions about which
lines should show up more, not something to guess at now.

## Attribute-flavored phrasing

Three event types have their own dedicated flavor table instead of a flat
bank, each keyed by which candidate attribute is highest for the relevant
player — implemented generically via `_FLAVORED_EVENT_TYPES` and
`CommentaryGenerator._dominant_flavor()` in `generator.py`, not as
per-event-type branches:

- `POSSESSION_PROGRESS` (`PROGRESSION_TEMPLATES_BY_FLAVOR`): the
  protagonist's Pace vs Dribbling vs Vision — "explodes past"/"races down
  the {phase}" for pace, "dances past"/"jinks past" for dribbling, "picks
  out"/"threads it through" for vision.
- `SHOT` (`SHOT_TEMPLATES_BY_FLAVOR`): the shooter's Shooting vs Composure
  — "strikes it with real power" for shooting, "calmly picks a spot" for
  composure.
- `FOUL` (`FOUL_TEMPLATES_BY_FLAVOR`): the tackler's Aggression alone (a
  single-candidate case — either it clears the threshold and reads
  "reckless"/"crunching," or it doesn't and phrasing stays neutral).

In every case, the winning attribute only earns its flavor if it clears
`FLAVOR_THRESHOLD` (70/99); below that, phrasing falls back to a generic
bank rather than reading as flashy (or reckless) for an unremarkable
player. This is what makes the same event type feel different depending on
which player and which attributes actually produced it — a direct payoff
of the engine exposing *why* a phase succeeded, not just *that* it did.
Remaining flat-bank event types (GOAL, CARD, INJURY...) are natural
candidates to extend this same way later, not done yet.

## Suspense pacing

Because the engine already emits one event per phase transition (see the
possession-chain state machine in `app/engine/CLAUDE.md`), tension is mostly
a byproduct of the phase structure itself: "enters the final third..." then
"shoots!" then the outcome, as three separate events/lines rather than one
flattened "shot, saved" event. Commentary should lean into this rather than
compress phases into single lines. The *delivery* layer (see
`app/delivery/CLAUDE.md`) is responsible for the actual timing/delay between
these lines — commentary just needs to keep phases as distinct, separately
described events.

## Scope for MVP

- English text only. Keep template logic free of hardcoded control flow that
  would make future localization harder (e.g. don't build sentences by
  string-concatenating fragments in an order that's English-specific;
  prefer whole-sentence templates with placeholders).
- No LLM-based generation. Static, weighted template banks are the whole
  scope for v1 — an LLM flavor pass is a plausible future extension, not
  something to build now.
