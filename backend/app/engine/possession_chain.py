"""PossessionChainEngine: runs one possession chain — one team's attempt to
go from their own third to a shot — through its phase transitions.

See engine/CLAUDE.md §5 for the full state diagram. This v1 slice covers
the progression phases and the shot; a turnover at any phase ends the
chain immediately (the other team gets the ball next). Fouls, offside, set
pieces, and rebounds are separate, not-yet-implemented roadmap items — see
Phase 1 in the README.

Every contest resolves through the same effective-rating pipeline: the
team/individual blend (engine/rating/CLAUDE.md §3), then tactical matchup
(§2), home advantage, weather, and fatigue as multipliers, with an
independent chance of a moment of brilliance spiking the attacking
protagonist's individual contribution beforehand. See brilliance.py,
home_advantage.py, and weather_modifiers.py for each piece.
"""

import random

from app.domain.match_context import MatchContext
from app.domain.player import Player
from app.domain.team import Team
from app.engine.brilliance import BONUS_MULTIPLIER, BrillianceCheck
from app.engine.events import EventType, MatchEvent
from app.engine.fatigue import FatigueModel
from app.engine.home_advantage import HomeAdvantage
from app.engine.phase import Phase
from app.engine.probability import ProbabilityModel
from app.engine.rating.calculator import PhaseRatingCalculator
from app.engine.rating.selector import ProtagonistSelector
from app.engine.rating.tables import BLEND, eligible_players
from app.engine.tactical_matchup import TacticalMatchup
from app.engine.weather_modifiers import WeatherModifiers

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


class _RatingResult:
    """Internal: an effective rating plus who (if anyone) produced a
    moment of brilliance while it was being computed, so callers can emit
    the right event without recomputing anything."""

    def __init__(self, value: float, brilliance_player: Player | None = None):
        self.value = value
        self.brilliance_player = brilliance_player


class PossessionChainEngine:
    def __init__(self) -> None:
        self._rating = PhaseRatingCalculator()
        self._selector = ProtagonistSelector()
        self._probability = ProbabilityModel()
        self._matchup = TacticalMatchup()
        self._fatigue = FatigueModel()
        self._brilliance = BrillianceCheck()
        self._home_advantage = HomeAdvantage()
        self._weather = WeatherModifiers()

    def run(
        self,
        minute: int,
        attacking: Team,
        defending: Team,
        rng: random.Random,
        home_team_id: str,
        context: MatchContext,
    ) -> ChainResult:
        events: list[MatchEvent] = []

        for phase in _PROGRESSION_PHASES:
            succeeded = self._contest(phase, minute, attacking, defending, rng, events, home_team_id, context)
            if not succeeded:
                return ChainResult(events, scored=False)

        shot_events, scored = self._resolve_shot(minute, attacking, defending, rng, home_team_id, context)
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
        home_team_id: str,
        context: MatchContext,
    ) -> bool:
        attacker_group = eligible_players(phase, attacking.starting_xi, "attack")
        defender_group = eligible_players(phase, defending.starting_xi, "defense")

        protagonist_attacker = self._selector.select(phase, attacking.starting_xi, "attack", rng)
        protagonist_defender = self._selector.select(phase, defending.starting_xi, "defense", rng)

        effective_attacker, effective_defender = self._effective_ratings(
            phase, attacking, defending, protagonist_attacker, protagonist_defender,
            attacker_group, defender_group, home_team_id, context, rng,
        )

        if effective_attacker.brilliance_player is not None:
            events.append(
                MatchEvent(
                    minute=minute,
                    type=EventType.MOMENT_OF_BRILLIANCE,
                    team_id=attacking.id,
                    player_ids=[effective_attacker.brilliance_player.id],
                    payload={"phase": phase.value},
                )
            )

        succeeded = self._probability.resolve(effective_attacker.value, effective_defender.value, rng)

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
        self,
        minute: int,
        attacking: Team,
        defending: Team,
        rng: random.Random,
        home_team_id: str,
        context: MatchContext,
    ) -> tuple[list[MatchEvent], bool]:
        phase = Phase.SHOT
        shooter = self._selector.select(phase, attacking.starting_xi, "attack", rng)
        keeper = self._selector.select(phase, defending.starting_xi, "defense", rng)

        effective_attacker, effective_defender = self._effective_ratings(
            phase, attacking, defending, shooter, keeper, [shooter], [keeper], home_team_id, context, rng,
        )

        events = []
        if effective_attacker.brilliance_player is not None:
            events.append(
                MatchEvent(minute=minute, type=EventType.MOMENT_OF_BRILLIANCE, team_id=attacking.id, player_ids=[shooter.id])
            )
        events.append(MatchEvent(minute=minute, type=EventType.SHOT, team_id=attacking.id, player_ids=[shooter.id]))

        scored = self._probability.resolve(effective_attacker.value, effective_defender.value, rng)
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
        home_team_id: str,
        context: MatchContext,
        rng: random.Random,
    ) -> tuple[_RatingResult, _RatingResult]:
        """The contest formula from engine/CLAUDE.md §4: team/individual
        blend, an independent brilliance check on the attacker, then the
        tactical-matchup/home-advantage/weather modifiers, then fatigue."""
        attacker_blend = self._blended_rating(phase, attacking, protagonist_attacker, "attack")
        defender_blend = self._blended_rating(phase, defending, protagonist_defender, "defense")

        brilliance_player = None
        if self._brilliance.roll(protagonist_attacker, rng):
            attacker_blend *= BONUS_MULTIPLIER
            brilliance_player = protagonist_attacker

        attacker_mod, defender_mod = self._matchup.modifiers(phase, attacking.tactic, defending.tactic)
        attacker_mod *= self._weather.attacker_modifier(phase, context.weather)
        attacker_mod *= self._home_advantage.modifier(attacking.id, home_team_id)
        defender_mod *= self._home_advantage.modifier(defending.id, home_team_id)

        attacker_fatigue = self._fatigue.average_multiplier(attacker_fatigue_group)
        defender_fatigue = self._fatigue.average_multiplier(defender_fatigue_group)

        effective_attacker = attacker_blend * attacker_mod * attacker_fatigue
        effective_defender = defender_blend * defender_mod * defender_fatigue
        return _RatingResult(effective_attacker, brilliance_player), _RatingResult(effective_defender)

    def _blended_rating(self, phase: Phase, team: Team, protagonist: Player, side: str) -> float:
        team_rating = self._rating.rate(phase, team.starting_xi, side)
        individual_rating = self._rating.individual_score(phase, protagonist, side)
        return BLEND * team_rating + (1 - BLEND) * individual_rating
