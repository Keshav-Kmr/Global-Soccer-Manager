"""Penalty kicks awarded for fouls inside the defending penalty area."""

from __future__ import annotations

import random

from app.domain.player import Player, Position
from app.domain.team import Team
from app.engine.events import EventType, MatchEvent
from app.engine.home_advantage import HomeAdvantage
from app.engine.match_situation import MatchSituation
from app.engine.phase import Phase
from app.engine.probability import ProbabilityModel
from app.engine.rating.calculator import PhaseRatingCalculator
from app.engine.weather_modifiers import WeatherModifiers

_PENALTY_DEPTH_FROM_GOAL = 16.0


def in_penalty_area(ball_x: float, *, attacks_right: bool) -> bool:
    if attacks_right:
        return ball_x >= 100.0 - _PENALTY_DEPTH_FROM_GOAL
    return ball_x <= _PENALTY_DEPTH_FROM_GOAL


def select_penalty_taker(team: Team) -> Player:
    available = [p for p in team.starting_xi if p.available]
    if not available:
        return team.starting_xi[0]
    return max(available, key=lambda p: p.attributes.shooting + p.attributes.composure)


class PenaltyEngine:
    def __init__(self) -> None:
        self._rating = PhaseRatingCalculator()
        self._probability = ProbabilityModel()
        self._home = HomeAdvantage()
        self._weather = WeatherModifiers()

    def resolve(
        self,
        minute: int,
        attacking: Team,
        defending: Team,
        rng: random.Random,
        situation: MatchSituation,
    ) -> tuple[list[MatchEvent], bool]:
        taker = select_penalty_taker(attacking)
        keeper = next(p for p in defending.starting_xi if p.position == Position.GK)

        events = [
            MatchEvent(
                minute=minute,
                type=EventType.PENALTY_AWARDED,
                team_id=attacking.id,
                player_ids=[taker.id],
                payload={"fouled_in_area": True},
            )
        ]

        shooter_rating = self._rating.individual_score(Phase.SHOT, taker, "attack")
        keeper_rating = self._rating.individual_score(Phase.SHOT, keeper, "defense")
        shooter_rating *= self._home.modifier(attacking.id, situation.home_team_id)
        keeper_rating *= self._home.modifier(defending.id, situation.home_team_id)
        shooter_rating *= self._weather.attacker_modifier(Phase.SHOT, situation.context.weather)

        scored = self._probability.resolve(shooter_rating, keeper_rating, rng)
        if scored:
            events.append(
                MatchEvent(
                    minute=minute,
                    type=EventType.PENALTY_GOAL,
                    team_id=attacking.id,
                    player_ids=[taker.id],
                )
            )
            return events, True

        if rng.random() < 0.55:
            events.append(
                MatchEvent(
                    minute=minute,
                    type=EventType.PENALTY_SAVE,
                    team_id=defending.id,
                    player_ids=[taker.id, keeper.id],
                )
            )
        else:
            events.append(
                MatchEvent(
                    minute=minute,
                    type=EventType.PENALTY_MISS,
                    team_id=attacking.id,
                    player_ids=[taker.id],
                )
            )
        return events, False