"""MatchSimulator: owns the full match loop, alternating possession chains
between both teams. See engine/CLAUDE.md §5 and the top-level module
contract ("calling this twice with the same arguments must yield identical
events, in identical order").

MINUTES_PER_CHAIN is a tuning constant, not a derived value — it controls
how many attacking sequences happen across 90 minutes and therefore how
many shots/goals a typical match produces. Treat it the same way as
SPREAD/P_MIN/P_MAX in probability.py: a first approximation to refine once
we can look at real simulated output (see scripts/simulate_demo.py and the
statistical tests in tests/engine/).
"""

import random

from app.domain.team import Team
from app.engine.events import EventType, MatchEvent
from app.engine.possession_chain import PossessionChainEngine

MATCH_MINUTES = 90
MINUTES_PER_CHAIN = 2


class MatchSimulator:
    def __init__(self) -> None:
        self._chain_engine = PossessionChainEngine()

    def simulate(self, team_a: Team, team_b: Team, seed: int) -> list[MatchEvent]:
        # Each call is a fresh 90 minutes: reset fitness so fatigue never
        # leaks in from a previous simulate() call sharing the same Team/
        # Player objects (as the statistical tests and the demo script do).
        # Persisting fatigue *across* matches is a future, season-level
        # concern, not something simulate() owns.
        for player in (*team_a.starting_xi, *team_b.starting_xi):
            player.fitness = 1.0

        rng = random.Random(seed)
        events: list[MatchEvent] = [MatchEvent(minute=0, type=EventType.KICKOFF, team_id=team_a.id)]

        possession, other = team_a, team_b
        minute = 0
        while minute < MATCH_MINUTES:
            minute += MINUTES_PER_CHAIN
            result = self._chain_engine.run(minute, possession, other, rng)
            events.extend(result.events)
            # Whether the chain ended in a goal, a turnover, or a missed
            # shot, the other side gets the next possession — see the
            # roadmap note on set pieces for the nuance this skips (e.g. a
            # blocked shot restarting as the same team's corner).
            possession, other = other, possession

        events.append(MatchEvent(minute=MATCH_MINUTES, type=EventType.FULL_TIME, team_id=None))
        return events
