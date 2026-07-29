from app.domain.match_context import Weather
from app.engine.phase import Phase
from app.engine.weather_modifiers import WeatherModifiers

_ALL_PHASES = (Phase.BUILD_UP, Phase.MIDFIELD, Phase.FINAL_THIRD, Phase.SHOT)


def test_rain_penalizes_progression_phases_but_not_the_shot():
    mods = WeatherModifiers()
    for phase in (Phase.BUILD_UP, Phase.MIDFIELD, Phase.FINAL_THIRD):
        assert mods.attacker_modifier(phase, Weather.RAIN) < 1.0
    assert mods.attacker_modifier(Phase.SHOT, Weather.RAIN) == 1.0


def test_wind_only_penalizes_the_shot():
    mods = WeatherModifiers()
    assert mods.attacker_modifier(Phase.SHOT, Weather.WIND) < 1.0
    for phase in (Phase.BUILD_UP, Phase.MIDFIELD, Phase.FINAL_THIRD):
        assert mods.attacker_modifier(phase, Weather.WIND) == 1.0


def test_clear_weather_never_changes_anything():
    mods = WeatherModifiers()
    for phase in _ALL_PHASES:
        assert mods.attacker_modifier(phase, Weather.CLEAR) == 1.0
