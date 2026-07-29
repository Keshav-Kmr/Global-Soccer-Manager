# Frontend

Not started. Stack (React / Vue / Svelte / other) is intentionally undecided
until the backend match engine MVP is validated end-to-end (a match can be
simulated and streamed over WebSocket, verified with a simple script or test
client).

## What it will eventually need to render

- Live score and match clock.
- A key-event ticker (goals, cards, substitutions, injuries).
- The phase-by-phase suspense text feed from `app/commentary` — this is the
  primary experience, not a secondary log. No pitch/field graphic is
  required; this is a text-and-tension presentation, not a visual match
  simulator.

Revisit this file and make real stack decisions once the backend side above
is working.
