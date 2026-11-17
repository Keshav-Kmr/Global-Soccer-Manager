"""Deterministic headless replay: same teams, seed, and optional manager actions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.domain.formation import Formation
from app.domain.match_context import MatchContext
from app.domain.player import Player
from app.domain.tactic import Tactic
from app.domain.team import Team
from app.engine.auto_substitution import MAX_SUBSTITUTIONS
from app.engine.match import Match


ReplayActionKind = Literal["tactic_change", "formation_change", "substitution"]


@dataclass
class ReplayAction:
    at_minute: int
    kind: ReplayActionKind
    team_id: str
    tactic: Tactic | None = None
    formation: Formation | None = None
    player_out_id: str | None = None
    player_in_id: str | None = None


def run_replay(
    team_a: Team,
    team_b: Team,
    seed: int,
    context: MatchContext | None = None,
    actions: list[ReplayAction] | None = None,
) -> Match:
    """Simulate to full time, applying each action once `minute >= at_minute`."""
    match = Match(team_a, team_b, seed, context)
    actions = sorted(actions or [], key=lambda a: a.at_minute)
    for action in actions:
        _advance_to_minute(match, action.at_minute)
        if match.finished:
            break
        _apply_action(match, action)

    while not match.finished:
        match.play_next_chain()
    return match


def _advance_to_minute(match: Match, target_minute: int) -> None:
    safety = 0
    while not match.finished and match.minute < target_minute and safety < 500:
        match.play_next_chain()
        safety += 1


def _apply_action(match: Match, action: ReplayAction) -> None:
    team = match.team_by_id(action.team_id)
    if team is None:
        raise ValueError(f"unknown team id {action.team_id!r}")

    if action.kind == "tactic_change":
        if action.tactic is None:
            raise ValueError("tactic_change requires tactic")
        match.change_tactic(team, action.tactic)
        return

    if action.kind == "formation_change":
        if action.formation is None:
            raise ValueError("formation_change requires formation")
        match.change_formation(team, action.formation)
        return

    if action.kind == "substitution":
        if not action.player_out_id or not action.player_in_id:
            raise ValueError("substitution requires player_out_id and player_in_id")
        if team.substitutions_used >= MAX_SUBSTITUTIONS:
            raise ValueError(f"substitution limit ({MAX_SUBSTITUTIONS}) reached")
        player_out = _find_player(team.starting_xi, action.player_out_id, "player_out")
        player_in = _find_player(team.bench, action.player_in_id, "player_in")
        if not player_out.available:
            raise ValueError("player_out is not available")
        match.substitute(team, player_out, player_in)
        team.bench.remove(player_in)
        team.bench.append(player_out)
        team.substitutions_used += 1
        return

    raise ValueError(f"unsupported replay action {action.kind!r}")


def _find_player(players: list[Player], player_id: str, label: str) -> Player:
    for player in players:
        if player.id == player_id:
            return player
    raise ValueError(f"{label} not found")