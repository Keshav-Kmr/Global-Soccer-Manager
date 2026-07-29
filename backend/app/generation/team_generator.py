"""Fictional player/team generation — this project uses no real-world
player data (root CLAUDE.md, README), so seeding the database with usable
content means procedurally inventing players. Deterministic given a
seeded random.Random, matching the RNG discipline used everywhere else in
this project (engine/CLAUDE.md) — including ids, which are derived from
the same RNG rather than `uuid.uuid4()` (which reads from `os.urandom`
and would silently break that determinism).
"""

import random

from app.domain.player import Player, PlayerAttributes, Position
from app.domain.tactic import Tactic
from app.domain.team import Team

_FIRST_NAMES = [
    "Aldo", "Bram", "Casimir", "Dario", "Emeka", "Fabio", "Gunnar", "Hendrik",
    "Ivo", "Jori", "Kasimir", "Luca", "Mateus", "Nando", "Oskar", "Pavel",
    "Quinten", "Rafi", "Santo", "Teodor", "Ulric", "Vito", "Wander", "Yannis",
]
_LAST_NAMES = [
    "Alverez", "Brandt", "Costin", "Dorner", "Eskander", "Falco", "Grimaldi",
    "Halvorsen", "Isaka", "Jarosz", "Kallas", "Lindqvist", "Marchetti", "Novak",
    "Odierno", "Petrescu", "Quintero", "Rybak", "Sundin", "Tavares", "Ulmer",
    "Vasquez", "Winters", "Zamora",
]

_FORMATION = [
    Position.GK,
    Position.CB, Position.CB, Position.FB, Position.FB,
    Position.DM, Position.CM, Position.CM,
    Position.W, Position.ST, Position.W,
]
_BENCH_POSITIONS = [Position.GK, Position.CB, Position.CM, Position.W, Position.ST]

_ATTRIBUTE_MIN = 1
_ATTRIBUTE_MAX = 99
# Standard deviation for attribute rolls around a team's quality tier —
# wide enough that generated squads have real individual variation
# (a generated "star" or "weak link"), not every player reading identical.
_ATTRIBUTE_SPREAD = 10


def _random_id(rng: random.Random) -> str:
    return f"{rng.getrandbits(64):016x}"


class PlayerGenerator:
    def __init__(self, rng: random.Random) -> None:
        self._rng = rng

    def generate(self, position: Position, quality: int) -> Player:
        name = f"{self._rng.choice(_FIRST_NAMES)} {self._rng.choice(_LAST_NAMES)}"
        is_gk = position == Position.GK
        attributes = PlayerAttributes(
            pace=self._roll(quality), dribbling=self._roll(quality), passing=self._roll(quality),
            vision=self._roll(quality), shooting=self._roll(quality), tackling=self._roll(quality),
            marking=self._roll(quality), strength=self._roll(quality), positioning=self._roll(quality),
            aggression=self._roll(quality), composure=self._roll(quality), stamina=self._roll(quality),
            flair=self._roll(quality),
            reflexes=self._roll(quality) if is_gk else _ATTRIBUTE_MIN,
            handling=self._roll(quality) if is_gk else _ATTRIBUTE_MIN,
            gk_positioning=self._roll(quality) if is_gk else _ATTRIBUTE_MIN,
        )
        return Player(id=_random_id(self._rng), name=name, position=position, attributes=attributes)

    def _roll(self, quality: int) -> int:
        value = round(self._rng.gauss(quality, _ATTRIBUTE_SPREAD))
        return max(_ATTRIBUTE_MIN, min(_ATTRIBUTE_MAX, value))


class TeamGenerator:
    def __init__(self, rng: random.Random) -> None:
        self._rng = rng
        self._player_generator = PlayerGenerator(rng)

    def generate(self, name: str, quality: int, tactic: Tactic | None = None) -> Team:
        """`quality` is the team's average rating (1-99) — individual
        players vary around it, so two teams of the same quality still
        feel different (a generated star here, a weak link there)."""
        starting_xi = [self._player_generator.generate(pos, quality) for pos in _FORMATION]
        bench = [self._player_generator.generate(pos, quality) for pos in _BENCH_POSITIONS]
        return Team(
            id=_random_id(self._rng), name=name, starting_xi=starting_xi, bench=bench, tactic=tactic or Tactic()
        )
