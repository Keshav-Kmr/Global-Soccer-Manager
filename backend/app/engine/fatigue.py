"""FatigueModel: converts remaining fitness into an effective-attribute
multiplier, and depletes fitness as players take part in phases.

See engine/CLAUDE.md §3. FLOOR ensures a tired player is worse, never
useless. Depletion rate is deliberately raised by high Tempo/Pressing —
those tactical choices cost stamina, which is what makes them a real
trade-off rather than a free upgrade.
"""

from app.domain.player import Player
from app.domain.tactic import Pressing, Tempo

FLOOR = 0.7
BASE_DEPLETION = 0.01

_TEMPO_COST = {Tempo.SLOW: 0.8, Tempo.NORMAL: 1.0, Tempo.FAST: 1.3}
_PRESSING_COST = {Pressing.LOW: 0.8, Pressing.MEDIUM: 1.0, Pressing.HIGH: 1.4}


class FatigueModel:
    def multiplier(self, fitness: float) -> float:
        return FLOOR + (1 - FLOOR) * fitness

    def average_multiplier(self, players: list[Player]) -> float:
        return sum(self.multiplier(p.fitness) for p in players) / len(players)

    def deplete(self, player: Player, tempo: Tempo, pressing: Pressing) -> None:
        cost = BASE_DEPLETION * _TEMPO_COST[tempo] * _PRESSING_COST[pressing]
        player.fitness = max(0.0, player.fitness - cost)
