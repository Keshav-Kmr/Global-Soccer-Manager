"""Match: a stateful, steppable simulation of one match.

MatchSimulator.simulate() (match_simulator.py) runs a match straight
through in one call — the right tool for tests, scripts, and an eventual
"give me the final result" API path. Match is the reusable primitive
underneath it, and it supports stopping *between* possession chains to
change a team's tactic or make a substitution, with the change taking
effect on the very next chain.

This works with no special plumbing because PossessionChainEngine always
reads `team.tactic` and `team.starting_xi` live off the Team object it's
given — never a snapshot taken at kickoff. Mutating those objects between
play_next_chain() calls (via change_tactic()/substitute() below, which is
just what they do) is all it takes. Tactics are therefore not a
match-start-only setting; they're read fresh on every single contest,
which is exactly what makes tactics "central" rather than cosmetic.
"""

import random

from app.domain.match_context import MatchContext
from app.domain.player import Player
from app.domain.tactic import Tactic
from app.domain.team import Team
from app.engine.auto_substitution import AutoSubstitution
from app.engine.events import EventType, MatchEvent
from app.engine.match_situation import MatchSituation
from app.engine.possession_chain import ChainResult, PossessionChainEngine

MATCH_MINUTES = 90
MINUTES_PER_CHAIN = 2

# Range for the once-per-match referee strictness draw (engine/CLAUDE.md
# §6) — a multiplier on foul severity when deciding cards. 1.0 is neutral;
# below/above that, a match is lenient/card-happy respectively.
_REFEREE_STRICTNESS_RANGE = (0.7, 1.3)


class Match:
    def __init__(
        self,
        team_a: Team,
        team_b: Team,
        seed: int,
        context: MatchContext | None = None,
    ) -> None:
        # A fresh 90 minutes: restore squad composition (undoing any
        # substitution from a previous Match reusing these Team objects)
        # and reset match-day player/team state, so nothing ever leaks in
        # from a prior Match. The *first* Match a Team ever plays snapshots
        # its current starting_xi/bench as the pristine reference — taken
        # here, not at Team construction, so any pre-match customization
        # (e.g. swapping in a hand-built star player right after
        # build_team()) is captured, not wiped out. Every later Match
        # reusing the same Team restores from that snapshot instead of
        # re-capturing whatever a previous match's substitutions left
        # behind — see Team.__post_init__.
        for team in (team_a, team_b):
            if team._original_starting_xi is None:
                team._original_starting_xi = list(team.starting_xi)
                team._original_bench = list(team.bench)
            else:
                team.starting_xi = list(team._original_starting_xi)
                team.bench = list(team._original_bench)
            team.substitutions_used = 0

        for player in (*team_a.starting_xi, *team_a.bench, *team_b.starting_xi, *team_b.bench):
            player.fitness = 1.0
            player.yellow_cards = 0
            player.available = True

        self.team_a = team_a
        self.team_b = team_b
        self._auto_substitution = AutoSubstitution()
        # Kept around so a caller can narrate the finished event list in a
        # second pass with a reproducible commentary RNG — see
        # app/commentary/generator.py's module docstring.
        self.seed = seed
        self.minute = 0
        self.events: list[MatchEvent] = [MatchEvent(minute=0, type=EventType.KICKOFF, team_id=team_a.id)]

        self._rng = random.Random(seed)
        self._chain_engine = PossessionChainEngine()
        self._possession, self._other = team_a, team_b
        self._situation = MatchSituation(
            home_team_id=team_a.id,
            context=context or MatchContext(),
            referee_strictness=self._rng.uniform(*_REFEREE_STRICTNESS_RANGE),
        )

    @property
    def finished(self) -> bool:
        return self.minute >= MATCH_MINUTES

    def play_next_chain(self) -> ChainResult:
        """Advances the match by one possession chain. Any change_tactic()
        or substitute() call made before this immediately affects it, since
        Team objects are read live — see the module docstring."""
        if self.finished:
            raise RuntimeError("match is already finished")

        self.minute += MINUTES_PER_CHAIN
        result = self._chain_engine.run(self.minute, self._possession, self._other, self._rng, self._situation)
        self.events.extend(result.events)
        self._handle_auto_substitutions(result)

        # A foul means the attacking team keeps the ball via the free kick
        # rather than conceding possession like a clean turnover would.
        if not result.possession_retained:
            self._possession, self._other = self._other, self._possession

        if self.finished:
            self.events.append(MatchEvent(minute=MATCH_MINUTES, type=EventType.FULL_TIME, team_id=None))

        return result

    def _handle_auto_substitutions(self, result: ChainResult) -> None:
        """Injury-triggered subs react to this chain's events; tiredness-
        triggered subs are checked for both teams regardless, since fatigue
        accumulates gradually rather than as a discrete event. See
        engine/auto_substitution.py and engine/CLAUDE.md §8."""
        for team in (self.team_a, self.team_b):
            for event in result.events:
                if event.type == EventType.INJURY and event.team_id == team.id:
                    injured_player = next(p for p in team.starting_xi if p.id == event.player_ids[0])
                    sub_event = self._auto_substitution.substitute_for_injury(team, self.minute, injured_player)
                    if sub_event is not None:
                        self.events.append(sub_event)

            sub_event = self._auto_substitution.substitute_for_tiredness(team, self.minute)
            if sub_event is not None:
                self.events.append(sub_event)

    def play_to_completion(self) -> list[MatchEvent]:
        while not self.finished:
            self.play_next_chain()
        return self.events

    def change_tactic(self, team: Team, tactic: Tactic) -> None:
        """Changes a team's tactic effective immediately — the next
        play_next_chain() call already uses it."""
        team.tactic = tactic
        self.events.append(
            MatchEvent(
                minute=self.minute,
                type=EventType.TACTIC_CHANGE,
                team_id=team.id,
                payload={"mentality": tactic.mentality.value, "pressing": tactic.pressing.value},
            )
        )

    def substitute(self, team: Team, player_out: Player, player_in: Player) -> None:
        """Swaps a starting player for another, effective immediately.
        Doesn't manage bench bookkeeping (removing player_in from a bench
        list, tracking substitutions used) — that's squad-management
        scope, not something the match simulation itself owns."""
        index = team.starting_xi.index(player_out)
        team.starting_xi[index] = player_in
        self.events.append(
            MatchEvent(
                minute=self.minute,
                type=EventType.SUBSTITUTION,
                team_id=team.id,
                player_ids=[player_out.id, player_in.id],
                payload={"reason": "manual"},
            )
        )
