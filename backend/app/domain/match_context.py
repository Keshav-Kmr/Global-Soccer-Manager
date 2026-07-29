"""MatchContext: match-wide conditions that belong to neither team.

Pure data, like the other domain models — see engine/weather_modifiers.py
for how `weather` actually affects a contest. Home/away is deliberately not
part of this: it's just whichever team is passed first to Match (see
engine/match.py), not a separate flag to keep in sync.
"""

from dataclasses import dataclass
from enum import Enum


class Weather(str, Enum):
    CLEAR = "clear"
    RAIN = "rain"
    WIND = "wind"


@dataclass(frozen=True)
class MatchContext:
    weather: Weather = Weather.CLEAR
