"""MatchSituation: match-wide facts that don't change between possession
chains — which team is home, the weather, and this match's referee
strictness — bundled so PossessionChainEngine.run() doesn't grow a new
parameter every time a match-wide concept is added (this is the third one,
after home advantage and weather; see engine/CLAUDE.md §4.2 and §6).
"""

from dataclasses import dataclass

from app.domain.match_context import MatchContext


@dataclass(frozen=True)
class MatchSituation:
    home_team_id: str
    context: MatchContext
    referee_strictness: float
