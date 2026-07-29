"""PossessionChainEngine: runs one possession chain — one team's attempt to
go from their own third to a shot — through its phase transitions.

See engine/CLAUDE.md §5 for the full state diagram. This v1 slice covers
the progression phases and the shot; a turnover at any phase ends the
chain immediately (the other team gets the ball next). Fouls, offside, set
pieces, and rebounds are separate, not-yet-implemented roadmap items — see
Phase 1 in the README.
"""

import random

from app.domain.player import Player
from app.domain.team import Team
from app.engine.events import EventType, MatchEvent
from app.engine.fatigue import FatigueModel
from app.engine.phase import Phase
from app.engine.probability import ProbabilityModel
from app.engine.rating.calculator import PhaseRatingCalculator
from app.engine.rating.selector import ProtagonistSelector
from app.engine.rating.tables import BLEND, eligible_players
from app.engine.tactical_matchup import TacticalMatchup

_PROGRESSION_PHASES = (Phase.BUILD_UP, Phase.MIDFIELD, Phase.FINAL_THIRD)

# Uniform for v1 — a shot that isn't a goal lands on one of these outcomes
# with equal probability. Weighting this by goalkeeper/shooter attributes
# is a plausible refinement once we're tuning against real match output.
_NON_GOAL_SHOT_OUTCOMES = (EventType.SAVE, EventType.BLOCK, EventType.OFF_TARGET)


class ChainResult:
    """Outcome of one full chain attempt."""

    def __init__(self, events: list[MatchEvent], scored: bool):
        self.events = events
        self.scored = scored


class PossessionChainEngine:
    def __init__(self) -> None:
        self._rating = PhaseRatingCalculator()
        self._selector = ProtagonistSelector()
        self._probability = ProbabilityModel()
        self._matchup = TacticalMatchup()
        self._fatigue = FatigueModel()

    def run(self, minute: int, attacking: Team, defending: Team, rng: random.Random) -> ChainResult:
        events: list[MatchEvent] = []

        for phase in _PROGRESSION_PHASES:
            succeeded = self._contest(phase, minute, attacking, defending, rng, events)
            if not succeeded:
                return ChainResult(events, scored=False)

        shot_events, scored = self._resolve_shot(minute, attacking, defending, rng)
        events.extend(shot_events)
        return ChainResult(events, scored=scored)

    def _contest(
        self,
        phase: Phase,
        minute: int,
        attacking: Team,
        defending: Team,
        rng: random.Random,
        events: list[MatchEvent],
    ) -> bool:
        attacker_group = eligible_players(phase, attacking.starting_xi, "attack")
        defender_group = eligible_players(phase, defending.starting_xi, "defense")

        protagonist_attacker = self._selector.select(phase, attacking.starting_xi, "attack", rng)
        protagonist_defender = self._selector.select(phase, defending.starting_xi, "defense", rng)

        effective_attacker, effective_defender = self._effective_ratings(
            phase, attacking, defending, protagonist_attacker, protagonist_defender,
            attacker_group, defender_group,
        )

        succeeded = self._probability.resolve(effective_attacker, effective_defender, rng)

        events.append(
            MatchEvent(
                minute=minute,
                type=EventType.POSSESSION_PROGRESS if succeeded else EventType.TURNOVER,
                team_id=attacking.id,
                player_ids=[protagonist_attacker.id if succeeded else protagonist_defender.id],
                payload={"phase": phase.value},
            )
        )

        for player in attacker_group:
            self._fatigue.deplete(player, attacking.tactic.tempo, attacking.tactic.pressing)
        for player in defender_group:
            self._fatigue.deplete(player, defending.tactic.tempo, defending.tactic.pressing)

        return succeeded

    def _resolve_shot(
        self, minute: int, attacking: Team, defending: Team, rng: random.Random
    ) -> tuple[list[MatchEvent], bool]:
        phase = Phase.SHOT
        shooter = self._selector.select(phase, attacking.starting_xi, "attack", rng)
        keeper = self._selector.select(phase, defending.starting_xi, "defense", rng)

        effective_attacker, effective_defender = self._effective_ratings(
            phase, attacking, defending, shooter, keeper, [shooter], [keeper],
        )

        events = [MatchEvent(minute=minute, type=EventType.SHOT, team_id=attacking.id, player_ids=[shooter.id])]

        scored = self._probability.resolve(effective_attacker, effective_defender, rng)
        if scored:
            events.append(MatchEvent(minute=minute, type=EventType.GOAL, team_id=attacking.id, player_ids=[shooter.id]))
        else:
            outcome = rng.choice(_NON_GOAL_SHOT_OUTCOMES)
            involved = [shooter.id, keeper.id] if outcome == EventType.SAVE else [shooter.id]
            events.append(MatchEvent(minute=minute, type=outcome, team_id=attacking.id, player_ids=involved))

        return events, scored

    def _effective_ratings(
        self,
        phase: Phase,
        attacking: Team,
        defending: Team,
        protagonist_attacker: Player,
        protagonist_defender: Player,
        attacker_fatigue_group: list[Player],
        defender_fatigue_group: list[Player],
    ) -> tuple[float, float]:
        """The contest formula from engine/CLAUDE.md §4: team/individual
        blend (§3 in engine/rating/CLAUDE.md), times the tactical-matchup
        modifier, times fatigue."""
        attacker_blend = self._blended_rating(phase, attacking, protagonist_attacker, "attack")
        defender_blend = self._blended_rating(phase, defending, protagonist_defender, "defense")

        attacker_mod, defender_mod = self._matchup.modifiers(phase, attacking.tactic, defending.tactic)

        attacker_fatigue = self._fatigue.average_multiplier(attacker_fatigue_group)
        defender_fatigue = self._fatigue.average_multiplier(defender_fatigue_group)

        effective_attacker = attacker_blend * attacker_mod * attacker_fatigue
        effective_defender = defender_blend * defender_mod * defender_fatigue
        return effective_attacker, effective_defender

    def _blended_rating(self, phase: Phase, team: Team, protagonist: Player, side: str) -> float:
        team_rating = self._rating.rate(phase, team.starting_xi, side)
        individual_rating = self._rating.individual_score(phase, protagonist, side)
        return BLEND * team_rating + (1 - BLEND) * individual_rating
