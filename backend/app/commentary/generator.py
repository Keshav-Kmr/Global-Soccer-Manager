"""CommentaryGenerator: turns a MatchEvent into a narrative text line.

See commentary/CLAUDE.md. Never decides game outcomes — purely a text
formatter over data the engine already produced. `roster` maps player id
-> Player so templates can reference names/attributes; MatchEvent
deliberately only carries ids, not full Player objects (see
engine/CLAUDE.md §10), so this is the layer that resolves them.

`rng` should be the match's shared random.Random instance if narrating
live as the match unfolds, or (since narrating a whole finished event list
in one pass — as scripts/menu.py does — happens after the engine's own rng
has already been fully consumed) a fresh `random.Random(match.seed)`: a
"clearly seeded child" per commentary/CLAUDE.md, which keeps the whole
match, commentary included, reproducible from one seed.
"""

import random
from typing import Callable

from app.commentary.templates import (
    FLAVOR_THRESHOLD,
    FOUL_TEMPLATES_BY_FLAVOR,
    PROGRESSION_TEMPLATES_BY_FLAVOR,
    SHOT_TEMPLATES_BY_FLAVOR,
    TEMPLATES,
)
from app.domain.player import Player, PlayerAttributes
from app.engine.events import EventType, MatchEvent


# For each flavored event type, the flavor is decided from event.player_ids[0]
# — the protagonist for POSSESSION_PROGRESS, the shooter for SHOT, the
# tackler for FOUL — using the given candidate attributes.
_FLAVORED_EVENT_TYPES = {
    EventType.POSSESSION_PROGRESS: (PROGRESSION_TEMPLATES_BY_FLAVOR, lambda a: {
        "pace": a.pace, "dribbling": a.dribbling, "vision": a.vision,
    }),
    EventType.SHOT: (SHOT_TEMPLATES_BY_FLAVOR, lambda a: {
        "shooting": a.shooting, "composure": a.composure,
    }),
    EventType.FOUL: (FOUL_TEMPLATES_BY_FLAVOR, lambda a: {"reckless": a.aggression}),
}


class CommentaryGenerator:
    def describe(self, event: MatchEvent, roster: dict[str, Player], rng: random.Random) -> str:
        if event.type in _FLAVORED_EVENT_TYPES:
            templates = self._flavored_templates(event, roster)
        else:
            templates = TEMPLATES[event.type]

        template = rng.choice(templates)
        return template.format(**self._context(event, roster))

    def _flavored_templates(self, event: MatchEvent, roster: dict[str, Player]) -> list[str]:
        bank, candidates_fn = _FLAVORED_EVENT_TYPES[event.type]
        player = roster.get(event.player_ids[0]) if event.player_ids else None
        flavor = self._dominant_flavor(player, candidates_fn)
        return bank[flavor]

    def _dominant_flavor(
        self, player: Player | None, candidates_fn: Callable[[PlayerAttributes], dict[str, int]]
    ) -> str:
        """Which attribute (if any) is strong enough to earn its own
        phrasing for this player — see commentary/CLAUDE.md on
        attribute-flavored phrasing."""
        if player is None:
            return "default"
        candidates = candidates_fn(player.attributes)
        best = max(candidates, key=candidates.get)
        return best if candidates[best] >= FLAVOR_THRESHOLD else "default"

    def _context(self, event: MatchEvent, roster: dict[str, Player]) -> dict[str, str]:
        """Every placeholder any template might use, resolved from the
        event's ids to player names. Unused keys are harmless — a
        template only ever references the ones it actually needs."""

        def name_at(index: int) -> str:
            if index >= len(event.player_ids):
                return ""
            player_id = event.player_ids[index]
            player = roster.get(player_id)
            return player.name if player else player_id

        return {
            "team": event.team_id or "",
            "phase": event.payload.get("phase", ""),
            "color": event.payload.get("color", ""),
            "player": name_at(0),
            "player2": name_at(1),
            "tackler": name_at(0),
            "victim": name_at(1),
            "keeper": name_at(1),
            "player_out": name_at(0),
            "player_in": name_at(1),
        }
