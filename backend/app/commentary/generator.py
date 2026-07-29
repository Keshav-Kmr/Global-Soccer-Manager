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

from app.commentary.templates import PROGRESSION_TEMPLATES_BY_FLAVOR, TEMPLATES, FLAVOR_THRESHOLD
from app.domain.player import Player
from app.engine.events import EventType, MatchEvent


class CommentaryGenerator:
    def describe(self, event: MatchEvent, roster: dict[str, Player], rng: random.Random) -> str:
        if event.type == EventType.POSSESSION_PROGRESS:
            templates = self._progression_templates(event, roster)
        else:
            templates = TEMPLATES[event.type]

        template = rng.choice(templates)
        return template.format(**self._context(event, roster))

    def _progression_templates(self, event: MatchEvent, roster: dict[str, Player]) -> list[str]:
        player = roster.get(event.player_ids[0]) if event.player_ids else None
        flavor = self._dominant_flavor(player)
        return PROGRESSION_TEMPLATES_BY_FLAVOR[flavor]

    def _dominant_flavor(self, player: Player | None) -> str:
        """Which attribute (if any) is strong enough to earn its own
        phrasing for this player — see commentary/CLAUDE.md on
        attribute-flavored phrasing."""
        if player is None:
            return "default"
        attrs = player.attributes
        candidates = {"pace": attrs.pace, "dribbling": attrs.dribbling, "vision": attrs.vision}
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
