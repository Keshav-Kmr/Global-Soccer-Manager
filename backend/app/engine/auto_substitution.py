"""AutoSubstitution: the automatic side of substitutions — injury-triggered
and tiredness-triggered — that Match.substitute() deliberately doesn't own
(that method is the low-level, unrestricted primitive for human/live
control; see engine/CLAUDE.md §8 and §11).

Two triggers, checked by Match after every possession chain:

- **Injury**: whenever a player becomes unavailable via INJURY, bring on a
  like-for-like bench player immediately if one exists. Never triggered by
  a red card — real football doesn't let you replace a sent-off player,
  the team simply plays short-handed.
- **Tiredness**: once a starter's fitness drops below a threshold, swap in
  a like-for-like bench player if one is available. Only the single most
  tired eligible starter is considered per check, so a team doesn't burn
  every substitution in one exhausted chain.

Both respect a per-team substitution limit (Team.substitutions_used), which
this class owns and increments — Match.substitute() does not.
"""

from app.domain.player import Player
from app.domain.team import Team
from app.engine.events import EventType, MatchEvent

MAX_SUBSTITUTIONS = 5

# Calibrated empirically against a full match (see engine/CLAUDE.md §8):
# even the most heavily-used player in a 90-minute match rarely drops
# below ~0.53 fitness given fatigue.py's current depletion rate, so 0.5
# would almost never fire. At 0.72, roughly a sixth of matches between
# evenly-matched sides produce at least one tiredness substitution — a
# starting point to keep refining, not a final answer.
TIREDNESS_FITNESS_THRESHOLD = 0.72


class AutoSubstitution:
    def substitute_for_injury(self, team: Team, minute: int, injured_player: Player) -> MatchEvent | None:
        return self._substitute(team, minute, injured_player, reason="injury")

    def substitute_for_tiredness(self, team: Team, minute: int) -> MatchEvent | None:
        """Finds the most fatigued eligible starter below the tiredness
        threshold and, if a like-for-like bench player exists, subs them
        off. Returns None if no starter is tired enough or no replacement
        is available."""
        tired_starters = [
            p for p in team.starting_xi
            if p.available and p.fitness < TIREDNESS_FITNESS_THRESHOLD
        ]
        if not tired_starters:
            return None

        most_tired = min(tired_starters, key=lambda p: p.fitness)
        return self._substitute(team, minute, most_tired, reason="tiredness")

    def _substitute(self, team: Team, minute: int, player_out: Player, reason: str) -> MatchEvent | None:
        if team.substitutions_used >= MAX_SUBSTITUTIONS:
            return None

        player_in = self._find_replacement(team, player_out)
        if player_in is None:
            return None

        index = team.starting_xi.index(player_out)
        team.starting_xi[index] = player_in
        team.bench.remove(player_in)
        team.bench.append(player_out)
        team.substitutions_used += 1

        return MatchEvent(
            minute=minute,
            type=EventType.SUBSTITUTION,
            team_id=team.id,
            player_ids=[player_out.id, player_in.id],
            payload={"reason": reason},
        )

    def _find_replacement(self, team: Team, player_out: Player) -> Player | None:
        for candidate in team.bench:
            if candidate.available and candidate.position == player_out.position:
                return candidate
        return None
