"""WeatherModifiers: match-wide conditions that affect certain phases
uniformly, regardless of either team's tactic.

Unlike TacticalMatchup (asymmetric between the two teams' choices), weather
applies the same way no matter who's attacking — it's a property of the
match, not a matchup. Kept as its own class/file rather than folded into
TacticalMatchup because it changes for a different reason (conditions, not
tactics) and has a different data source (MatchContext, not Tactic).
"""

from app.domain.match_context import Weather
from app.engine.phase import Phase

_RAIN_AFFECTED_PHASES = (Phase.BUILD_UP, Phase.MIDFIELD, Phase.FINAL_THIRD)
_RAIN_PENALTY = 0.92
_WIND_SHOT_PENALTY = 0.90


class WeatherModifiers:
    def attacker_modifier(self, phase: Phase, weather: Weather) -> float:
        """Rain makes ball retention/progression harder (slicker pitch,
        harder passing); wind makes shooting less reliable. Neither
        affects the defending side directly — a defender's job doesn't
        get harder in the rain the way an attacker's does."""
        if weather == Weather.RAIN and phase in _RAIN_AFFECTED_PHASES:
            return _RAIN_PENALTY
        if weather == Weather.WIND and phase == Phase.SHOT:
            return _WIND_SHOT_PENALTY
        return 1.0
