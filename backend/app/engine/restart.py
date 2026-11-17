"""Lightweight IFAB-style restarts (Laws 8–17) for the possession-chain model.

We do not simulate Law 9 geometry, dropped balls, or 2026/27 timing protocols.
Restarts are *structural*: they emit narrative events, place the ball on the
pitch grid, choose who attacks next, and optionally skip to a later chain phase
(corner / shooting-range free kick). See engine/CLAUDE.md §5 and §7.
"""

from __future__ import annotations

import random
from enum import Enum

from app.engine.events import EventType, MatchEvent
from app.engine.phase import Phase

_THROW_IN_BUILD_UP_CHANCE = 0.18
_THROW_IN_MIDFIELD_WIDE_CHANCE = 0.12
_WIDE_TOUCHLINE_Y = 28.0


class RestartKind(str, Enum):
    KICKOFF = "kickoff"
    FREE_KICK = "free_kick"
    GOAL_KICK = "goal_kick"
    CORNER_KICK = "corner_kick"
    THROW_IN = "throw_in"


def restart_event(
    minute: int,
    *,
    kind: RestartKind,
    team_id: str,
    direct: bool = True,
    reason: str | None = None,
) -> MatchEvent:
    event_type = EventType(kind.value)
    payload: dict = {"direct": direct}
    if reason:
        payload["reason"] = reason
    return MatchEvent(minute=minute, type=event_type, team_id=team_id, payload=payload)


def shot_outcome_restart(outcome: EventType) -> RestartKind:
    if outcome == EventType.BLOCK:
        return RestartKind.CORNER_KICK
    return RestartKind.GOAL_KICK


def entry_phase_for_restart(kind: RestartKind, *, foul_phase: Phase | None = None) -> Phase:
    if kind == RestartKind.CORNER_KICK:
        return Phase.FINAL_THIRD
    if kind == RestartKind.FREE_KICK and foul_phase == Phase.FINAL_THIRD:
        return Phase.FINAL_THIRD
    if kind == RestartKind.THROW_IN:
        return Phase.BUILD_UP
    return Phase.BUILD_UP


def maybe_throw_in_on_turnover(
    phase: Phase,
    ball_y: float,
    rng: random.Random,
) -> bool:
    if phase == Phase.BUILD_UP and rng.random() < _THROW_IN_BUILD_UP_CHANCE:
        return True
    if phase == Phase.MIDFIELD and abs(ball_y - 50.0) >= _WIDE_TOUCHLINE_Y:
        return rng.random() < _THROW_IN_MIDFIELD_WIDE_CHANCE
    return False


def ball_coords_for_restart(
    kind: RestartKind,
    *,
    attacks_right: bool,
    entry: Phase,
) -> tuple[float, float]:
    """Rough normalized positions for the UI — not Law 1 dimensions."""
    if kind == RestartKind.KICKOFF:
        return 50.0, 50.0
    if kind == RestartKind.CORNER_KICK:
        cy = 6.0 if attacks_right else 94.0
        side_y = 8.0 if attacks_right else 92.0
        return cy, side_y
    if kind == RestartKind.GOAL_KICK:
        gx = 8.0 if attacks_right else 92.0
        return gx, 50.0
    if kind == RestartKind.THROW_IN:
        tx = 35.0 if entry == Phase.BUILD_UP else 55.0
        if not attacks_right:
            tx = 100.0 - tx
        return tx, 12.0 if attacks_right else 88.0
    # Free kick default — near last phase depth
    depth = {Phase.BUILD_UP: 30.0, Phase.MIDFIELD: 50.0, Phase.FINAL_THIRD: 70.0}.get(entry, 55.0)
    if not attacks_right:
        depth = 100.0 - depth
    return depth, 50.0