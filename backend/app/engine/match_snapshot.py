"""Save/load in-progress match state for deterministic resume."""

from __future__ import annotations

from app.domain.match_context import MatchContext, Weather
from app.domain.team import Team
from app.engine.clock import MatchClock, MatchPeriod
from app.engine.events import EventType, MatchEvent
from app.engine.match import Match
from app.engine.match_situation import MatchSituation
from app.engine.pitch import PitchModel, PitchState
from app.engine.statistics import MatchStatistics, PlayerStatistics, TeamStatistics


def _serialize_rng_state(state: tuple) -> list:
    version, internal, gauss = state
    return [version, list(internal), gauss]


def _deserialize_rng_state(data: list | tuple) -> tuple:
    if isinstance(data, tuple):
        return data
    version, internal, gauss = data
    return int(version), tuple(internal), gauss


def _event_to_dict(event: MatchEvent) -> dict:
    return {
        "minute": event.minute,
        "type": event.type.value,
        "team_id": event.team_id,
        "player_ids": list(event.player_ids),
        "payload": dict(event.payload),
    }


def _event_from_dict(data: dict) -> MatchEvent:
    return MatchEvent(
        minute=data["minute"],
        type=EventType(data["type"]),
        team_id=data.get("team_id"),
        player_ids=list(data.get("player_ids", [])),
        payload=dict(data.get("payload", {})),
    )


def export_snapshot(match: Match) -> dict:
    players = {}
    for player in (
        *match.team_a.starting_xi,
        *match.team_a.bench,
        *match.team_b.starting_xi,
        *match.team_b.bench,
    ):
        players[player.id] = {
            "fitness": player.fitness,
            "yellow_cards": player.yellow_cards,
            "available": player.available,
        }

    team_stats = {}
    for tid, ts in match.statistics.teams.items():
        team_stats[tid] = {
            "goals": ts.goals,
            "shots": ts.shots,
            "shots_on_target": ts.shots_on_target,
            "fouls": ts.fouls,
            "yellow_cards": ts.yellow_cards,
            "red_cards": ts.red_cards,
            "possession_chains": ts.possession_chains,
            "passes_completed": ts.passes_completed,
            "passes_attempted": ts.passes_attempted,
            "offsides": ts.offsides,
            "penalties_awarded": ts.penalties_awarded,
            "saves": ts.saves,
            "tackles": ts.tackles,
            "blocked_shots": ts.blocked_shots,
            "shots_off_target": ts.shots_off_target,
        }

    player_stats = {
        pid: {
            "minutes_played": ps.minutes_played,
            "goals": ps.goals,
            "shots": ps.shots,
            "shots_on_target": ps.shots_on_target,
            "fouls_committed": ps.fouls_committed,
            "yellow_cards": ps.yellow_cards,
            "red_cards": ps.red_cards,
        }
        for pid, ps in match.statistics.players.items()
    }

    return {
        "version": 1,
        "seed": match.seed,
        "rng_state": _serialize_rng_state(match._rng.getstate()),
        "paused": match._paused,
        "clock": {
            "minute": match._clock.minute,
            "period": match._clock.period.value,
            "first_half_stoppage": match._clock.first_half_stoppage,
            "second_half_stoppage": match._clock.second_half_stoppage,
            "interruption_seconds": match._clock._interruption_seconds,
            "halftime_minute": match._clock.halftime_minute,
        },
        "possession_team_id": match._possession.id,
        "referee_strictness": match._situation.referee_strictness,
        "weather": match._situation.context.weather.value,
        "events": [_event_to_dict(e) for e in match.events],
        "statistics": {"teams": team_stats, "players": player_stats, "last_minute": match.statistics._last_minute},
        "pitch": match._pitch.state.to_payload(),
        "players": players,
        "substitutions_used": {
            match.team_a.id: match.team_a.substitutions_used,
            match.team_b.id: match.team_b.substitutions_used,
        },
    }


def restore_snapshot(match: Match, snapshot: dict) -> None:
    """Overwrite `match` in-memory state from `snapshot` (same teams + seed as when exported)."""
    if snapshot["seed"] != match.seed:
        raise ValueError("snapshot seed does not match match seed")

    match._rng.setstate(_deserialize_rng_state(snapshot["rng_state"]))
    match._paused = snapshot["paused"]

    clock = match._clock
    clock_data = snapshot["clock"]
    clock.minute = clock_data["minute"]
    clock.period = MatchPeriod(clock_data["period"])
    clock.first_half_stoppage = clock_data["first_half_stoppage"]
    clock.second_half_stoppage = clock_data["second_half_stoppage"]
    clock._interruption_seconds = clock_data["interruption_seconds"]
    clock.halftime_minute = clock_data.get("halftime_minute")

    match._situation = MatchSituation(
        home_team_id=match.team_a.id,
        context=MatchContext(weather=Weather(snapshot["weather"])),
        referee_strictness=snapshot["referee_strictness"],
    )

    for team in (match.team_a, match.team_b):
        team.substitutions_used = snapshot["substitutions_used"][team.id]
        for player in (*team.starting_xi, *team.bench):
            state = snapshot["players"].get(player.id)
            if state:
                player.fitness = state["fitness"]
                player.yellow_cards = state["yellow_cards"]
                player.available = state["available"]

    possession_id = snapshot["possession_team_id"]
    match._possession = match.team_a if possession_id == match.team_a.id else match.team_b
    match._other = match.team_b if match._possession is match.team_a else match.team_a

    match.events = [_event_from_dict(e) for e in snapshot["events"]]

    stats = match.statistics
    stats._last_minute = snapshot["statistics"]["last_minute"]
    stats.teams.clear()
    for tid, raw in snapshot["statistics"]["teams"].items():
        stats.teams[tid] = TeamStatistics(
            goals=raw["goals"],
            shots=raw["shots"],
            shots_on_target=raw["shots_on_target"],
            fouls=raw["fouls"],
            yellow_cards=raw["yellow_cards"],
            red_cards=raw["red_cards"],
            possession_chains=raw["possession_chains"],
            passes_completed=raw["passes_completed"],
            passes_attempted=raw["passes_attempted"],
            offsides=raw.get("offsides", 0),
            penalties_awarded=raw.get("penalties_awarded", 0),
            saves=raw.get("saves", 0),
            tackles=raw.get("tackles", 0),
            blocked_shots=raw.get("blocked_shots", 0),
            shots_off_target=raw.get("shots_off_target", 0),
        )
    stats.players.clear()
    for pid, raw in snapshot["statistics"]["players"].items():
        stats.players[pid] = PlayerStatistics(**raw)

    pitch = snapshot["pitch"]
    match._pitch.state = PitchState(
        ball_x=pitch["ball"]["x"],
        ball_y=pitch["ball"]["y"],
        possession_team_id=pitch.get("possession_team_id"),
        ball_carrier_id=pitch.get("ball_carrier_id"),
        players={pid: {"x": pos["x"], "y": pos["y"]} for pid, pos in pitch.get("players", {}).items()},
    )