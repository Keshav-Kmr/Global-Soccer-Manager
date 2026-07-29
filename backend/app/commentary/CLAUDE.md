# Commentary

Turns a `MatchEvent` (structured data from `app/engine`) into a narrative
text line. This is a deliberately separate layer from the engine: the engine
must never format strings, and the commentary layer must never decide game
outcomes. That separation is what makes both sides independently testable
and lets commentary style evolve (more variety, later localization, maybe a
future LLM-based flavor pass) without ever touching simulation logic.

```python
def describe(event: MatchEvent, rng: random.Random) -> str:
    ...
```

`describe` takes the *same* `random.Random` instance used by the engine for
that match (or a clearly seeded child of it) so that the full match,
commentary included, stays reproducible from a single seed.

## Template bank approach

Each `MatchEvent` type has a bank of multiple template variants. One is
chosen (weighted, via the match's RNG) per event to avoid repetitive-sounding
matches:

```
SHOT templates for a "dribble-created" chance:
  "{player} dances past a challenge and gets a shot away!"
  "{player} jinks inside and lets fly!"

SHOT templates for a "through-ball-created" chance:
  "{player} is played in behind... and shoots!"
  "{player} races onto the through ball!"
```

## Attribute-flavored phrasing

Select the template *category* based on which attribute dominated the phase
that created the event, not just the event type. A pacey player's
progression reads differently from a technical dribbler's:

- Pace-dominant progression -> "explodes past", "races down the wing"
- Dribbling-dominant progression -> "dances past", "jinks past"
- Vision-dominant chance creation -> "picks out", "threads a pass to"

This is what makes the same event type feel different depending on which
player and which attributes actually produced it — a direct payoff of the
engine exposing *why* a phase succeeded, not just *that* it did.

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
