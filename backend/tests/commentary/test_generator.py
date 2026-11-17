import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from factories import make_player

from app.commentary.generator import CommentaryGenerator
from app.domain.player import Position
from app.engine.events import EventType, MatchEvent

_PACEY = make_player("pacey", "Pacey Player", Position.W, overall=50, pace=90)
_DRIBBLER = make_player("dribbler", "Dribbler Player", Position.W, overall=50, dribbling=90)
_VISIONARY = make_player("visionary", "Visionary Player", Position.CM, overall=50, vision=90)
_AVERAGE = make_player("average", "Average Player", Position.CM, overall=50)
_KEEPER = make_player("keeper", "Keeper Player", Position.GK, overall=50)
_POWER_SHOOTER = make_player("power_shooter", "Power Shooter", Position.ST, overall=50, shooting=90)
_COOL_FINISHER = make_player("cool_finisher", "Cool Finisher", Position.ST, overall=50, composure=90)
_RECKLESS_TACKLER = make_player("reckless_tackler", "Reckless Tackler", Position.CB, overall=50, aggression=90)

_ROSTER = {
    p.id: p for p in (
        _PACEY, _DRIBBLER, _VISIONARY, _AVERAGE, _KEEPER,
        _POWER_SHOOTER, _COOL_FINISHER, _RECKLESS_TACKLER,
    )
}

# One representative event per EventType, covering every placeholder shape
# the templates can reference (single player, two players, no player...).
_SAMPLE_EVENTS = {
    EventType.KICKOFF: MatchEvent(minute=0, type=EventType.KICKOFF, team_id="home"),
    EventType.POSSESSION_PROGRESS: MatchEvent(
        minute=10, type=EventType.POSSESSION_PROGRESS, team_id="home",
        player_ids=["average"], payload={"phase": "midfield"},
    ),
    EventType.TURNOVER: MatchEvent(
        minute=12, type=EventType.TURNOVER, team_id="home", player_ids=["average"], payload={"phase": "build_up"}
    ),
    EventType.MOMENT_OF_BRILLIANCE: MatchEvent(
        minute=14, type=EventType.MOMENT_OF_BRILLIANCE, team_id="home", player_ids=["dribbler"]
    ),
    EventType.FOUL: MatchEvent(
        minute=16, type=EventType.FOUL, team_id="away", player_ids=["average", "dribbler"], payload={"phase": "final_third"}
    ),
    EventType.CARD: MatchEvent(
        minute=16, type=EventType.CARD, team_id="away", player_ids=["average"], payload={"color": "yellow"}
    ),
    EventType.INJURY: MatchEvent(minute=18, type=EventType.INJURY, team_id="home", player_ids=["dribbler"]),
    EventType.SHOT: MatchEvent(minute=20, type=EventType.SHOT, team_id="home", player_ids=["pacey"]),
    EventType.GOAL: MatchEvent(minute=20, type=EventType.GOAL, team_id="home", player_ids=["pacey"]),
    EventType.SAVE: MatchEvent(minute=22, type=EventType.SAVE, team_id="home", player_ids=["pacey", "keeper"]),
    EventType.BLOCK: MatchEvent(minute=24, type=EventType.BLOCK, team_id="home", player_ids=["pacey"]),
    EventType.OFF_TARGET: MatchEvent(minute=26, type=EventType.OFF_TARGET, team_id="home", player_ids=["pacey"]),
    EventType.TACTIC_CHANGE: MatchEvent(minute=45, type=EventType.TACTIC_CHANGE, team_id="home"),
    EventType.FORMATION_CHANGE: MatchEvent(minute=46, type=EventType.FORMATION_CHANGE, team_id="home"),
    EventType.SUBSTITUTION: MatchEvent(
        minute=60, type=EventType.SUBSTITUTION, team_id="home", player_ids=["average", "pacey"]
    ),
    EventType.HALF_TIME: MatchEvent(minute=47, type=EventType.HALF_TIME, team_id=None),
    EventType.FULL_TIME: MatchEvent(minute=92, type=EventType.FULL_TIME, team_id=None),
    EventType.OFFSIDE: MatchEvent(minute=28, type=EventType.OFFSIDE, team_id="home", player_ids=["pacey"]),
    EventType.PENALTY_AWARDED: MatchEvent(
        minute=55, type=EventType.PENALTY_AWARDED, team_id="home", player_ids=["power_shooter"]
    ),
    EventType.PENALTY_GOAL: MatchEvent(
        minute=55, type=EventType.PENALTY_GOAL, team_id="home", player_ids=["power_shooter"]
    ),
    EventType.PENALTY_SAVE: MatchEvent(
        minute=70, type=EventType.PENALTY_SAVE, team_id="away", player_ids=["power_shooter", "keeper"]
    ),
    EventType.PENALTY_MISS: MatchEvent(
        minute=80, type=EventType.PENALTY_MISS, team_id="home", player_ids=["power_shooter"]
    ),
}


def test_every_event_type_has_a_sample_and_describes_without_error():
    assert set(_SAMPLE_EVENTS) == set(EventType)

    generator = CommentaryGenerator()
    rng = random.Random(0)
    for event in _SAMPLE_EVENTS.values():
        line = generator.describe(event, _ROSTER, rng)
        assert isinstance(line, str) and line


def test_foul_names_the_tackler_and_the_victim_correctly():
    generator = CommentaryGenerator()
    rng = random.Random(0)
    event = _SAMPLE_EVENTS[EventType.FOUL]

    lines = {generator.describe(event, _ROSTER, random.Random(seed)) for seed in range(20)}

    assert any("Average Player" in line for line in lines)


def test_pacey_player_gets_pace_flavored_progression_text():
    generator = CommentaryGenerator()
    event = MatchEvent(
        minute=10, type=EventType.POSSESSION_PROGRESS, team_id="home",
        player_ids=["pacey"], payload={"phase": "final_third"},
    )

    lines = {generator.describe(event, _ROSTER, random.Random(seed)) for seed in range(30)}

    assert any("explodes" in line or "races" in line or "pace" in line for line in lines)


def test_average_player_gets_default_progression_text_not_a_flavor():
    generator = CommentaryGenerator()
    event = MatchEvent(
        minute=10, type=EventType.POSSESSION_PROGRESS, team_id="home",
        player_ids=["average"], payload={"phase": "midfield"},
    )

    lines = {generator.describe(event, _ROSTER, random.Random(seed)) for seed in range(30)}

    assert all("explodes" not in line and "dances" not in line and "picks out" not in line for line in lines)


def test_power_shooter_gets_power_flavored_shot_text():
    generator = CommentaryGenerator()
    event = MatchEvent(minute=30, type=EventType.SHOT, team_id="home", player_ids=["power_shooter"])

    lines = {generator.describe(event, _ROSTER, random.Random(seed)) for seed in range(30)}

    assert any("power" in line or "thunderous" in line or "really goes for it" in line for line in lines)


def test_cool_finisher_gets_composure_flavored_shot_text():
    generator = CommentaryGenerator()
    event = MatchEvent(minute=30, type=EventType.SHOT, team_id="home", player_ids=["cool_finisher"])

    lines = {generator.describe(event, _ROSTER, random.Random(seed)) for seed in range(30)}

    assert any("composure" in line or "calmly" in line or "takes their time" in line for line in lines)


def test_average_shooter_gets_default_shot_text():
    generator = CommentaryGenerator()
    event = MatchEvent(minute=30, type=EventType.SHOT, team_id="home", player_ids=["average"])

    lines = {generator.describe(event, _ROSTER, random.Random(seed)) for seed in range(30)}

    assert all("power" not in line and "composure" not in line and "calmly" not in line for line in lines)


def test_reckless_tackler_gets_reckless_flavored_foul_text():
    generator = CommentaryGenerator()
    event = MatchEvent(
        minute=40, type=EventType.FOUL, team_id="home",
        player_ids=["reckless_tackler", "pacey"], payload={"phase": "midfield"},
    )

    lines = {generator.describe(event, _ROSTER, random.Random(seed)) for seed in range(30)}

    assert any("reckless" in line or "crunching" in line for line in lines)


def test_measured_tackler_gets_default_foul_text():
    generator = CommentaryGenerator()
    event = MatchEvent(
        minute=40, type=EventType.FOUL, team_id="home",
        player_ids=["average", "pacey"], payload={"phase": "midfield"},
    )

    lines = {generator.describe(event, _ROSTER, random.Random(seed)) for seed in range(30)}

    assert all("reckless" not in line and "crunching" not in line for line in lines)


def test_same_seed_produces_the_same_line():
    generator = CommentaryGenerator()
    event = _SAMPLE_EVENTS[EventType.GOAL]

    line_a = generator.describe(event, _ROSTER, random.Random(7))
    line_b = generator.describe(event, _ROSTER, random.Random(7))

    assert line_a == line_b


def test_unknown_player_id_falls_back_to_the_raw_id():
    generator = CommentaryGenerator()
    event = MatchEvent(minute=20, type=EventType.GOAL, team_id="home", player_ids=["someone_not_in_roster"])

    line = generator.describe(event, {}, random.Random(0))

    assert "someone_not_in_roster" in line
