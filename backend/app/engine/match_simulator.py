"""MatchSimulator: convenience wrapper for running a match start-to-finish
in one call, with no mid-match interaction.

For live tactic changes or substitutions between possession chains, use
Match directly (match.py) — that's the actual stateful primitive; this
class just runs one to completion.
"""

from app.domain.match_context import MatchContext
from app.domain.team import Team
from app.engine.events import MatchEvent
from app.engine.match import Match


class MatchSimulator:
    def simulate(
        self, team_a: Team, team_b: Team, seed: int, context: MatchContext | None = None
    ) -> list[MatchEvent]:
        return Match(team_a, team_b, seed, context).play_to_completion()
