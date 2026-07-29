"""Test-only helpers for building players/teams with hand-set stats.

Not part of the engine's public API — just a shared way for tests (and
scripts/simulate_demo.py, which keeps its own copy so it stays runnable
standalone) to avoid retyping all twelve attributes for every player.
"""

from app.domain.player import Player, PlayerAttributes, Position
from app.domain.tactic import Tactic
from app.domain.team import Team

_FORMATION_4_3_3 = [
    Position.GK,
    Position.CB, Position.CB, Position.FB, Position.FB,
    Position.DM, Position.CM, Position.CM,
    Position.W, Position.ST, Position.W,
]

# A small bench covering the positions most likely to need a like-for-like
# replacement (engine/auto_substitution.py) — not a full matchday squad.
_BENCH_POSITIONS = [Position.GK, Position.CB, Position.CM, Position.W, Position.ST]


def make_player(player_id: str, name: str, position: Position, overall: int, **overrides) -> Player:
    """A player with every attribute set to `overall`, unless overridden."""
    attrs = dict(
        pace=overall, dribbling=overall, passing=overall, vision=overall,
        shooting=overall, tackling=overall, marking=overall, strength=overall,
        positioning=overall, aggression=overall, composure=overall, stamina=overall,
        flair=overall, reflexes=overall, handling=overall, gk_positioning=overall,
    )
    attrs.update(overrides)
    return Player(id=player_id, name=name, position=position, attributes=PlayerAttributes(**attrs))


def build_team(team_id: str, name: str, overall: int, tactic: Tactic | None = None) -> Team:
    """An 11-player 4-3-3 squad plus a small bench, every player rated `overall`."""
    players = [
        make_player(f"{team_id}_{i}", f"{name} #{i}", position, overall)
        for i, position in enumerate(_FORMATION_4_3_3)
    ]
    bench = [
        make_player(f"{team_id}_sub{i}", f"{name} Sub {i}", position, overall)
        for i, position in enumerate(_BENCH_POSITIONS)
    ]
    return Team(id=team_id, name=name, starting_xi=players, tactic=tactic or Tactic(), bench=bench)
