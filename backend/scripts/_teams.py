"""Shared team/player builders for the manual test scripts in this folder
(simulate_demo.py, menu.py). Not part of the engine's public API — just a
way to avoid retyping all twelve attributes for every player by hand.
"""

from app.domain.player import Player, PlayerAttributes, Position
from app.domain.tactic import Tactic
from app.domain.team import Team

FORMATION_4_3_3 = [
    Position.GK,
    Position.CB, Position.CB, Position.FB, Position.FB,
    Position.DM, Position.CM, Position.CM,
    Position.W, Position.ST, Position.W,
]


def make_player(player_id: str, name: str, position: Position, overall: int, **overrides) -> Player:
    """A player with every attribute set to `overall`, unless overridden
    (e.g. make_player(..., shooting=95, pace=90) for a hand-picked star)."""
    attrs = dict(
        pace=overall, dribbling=overall, passing=overall, vision=overall,
        shooting=overall, tackling=overall, marking=overall, strength=overall,
        positioning=overall, aggression=overall, composure=overall, stamina=overall,
        reflexes=overall, handling=overall, gk_positioning=overall,
    )
    attrs.update(overrides)
    return Player(id=player_id, name=name, position=position, attributes=PlayerAttributes(**attrs))


def build_team(team_id: str, name: str, overall: int, tactic: Tactic | None = None) -> Team:
    """An 11-player 4-3-3 squad with every player rated `overall`. Swap any
    entry in the returned team's `starting_xi` to give a specific player
    different stats (see menu.py's star-striker scenario)."""
    players = [
        make_player(f"{team_id}_{i}", f"{name} #{i}", position, overall)
        for i, position in enumerate(FORMATION_4_3_3)
    ]
    return Team(id=team_id, name=name, starting_xi=players, tactic=tactic or Tactic())
