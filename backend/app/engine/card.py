"""CardCheck: given a foul's severity and this match's referee strictness,
decides no card / yellow / red. See engine/CLAUDE.md §6.

Stateless — accumulating a second yellow into a red is match-day player
state (Player.yellow_cards), owned by the caller (possession_chain.py),
not this class.

Referee strictness is a single value drawn once per match (see
engine/match.py) from a reasonable range, so some matches are just
card-happy and others let a lot go — this is deliberately part of the
variance pillar (root CLAUDE.md), not noise to average away.
"""

import random
from enum import Enum

BASE_YELLOW_CHANCE = 0.15
BASE_RED_CHANCE = 0.02
SEVERITY_YELLOW_SCALE = 0.45
SEVERITY_RED_SCALE = 0.10
MAX_YELLOW_CHANCE = 0.85
MAX_RED_CHANCE = 0.30


class Card(str, Enum):
    NONE = "none"
    YELLOW = "yellow"
    RED = "red"


class CardCheck:
    def roll(self, severity: float, referee_strictness: float, rng: random.Random) -> Card:
        danger = severity * referee_strictness

        p_red = min(MAX_RED_CHANCE, BASE_RED_CHANCE + SEVERITY_RED_SCALE * danger)
        p_yellow = min(MAX_YELLOW_CHANCE, BASE_YELLOW_CHANCE + SEVERITY_YELLOW_SCALE * danger)

        roll = rng.random()
        if roll < p_red:
            return Card.RED
        if roll < p_red + p_yellow:
            return Card.YELLOW
        return Card.NONE
