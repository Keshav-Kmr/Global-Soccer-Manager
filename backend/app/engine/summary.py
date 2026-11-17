"""Read-only helpers for interpreting a MatchEvent stream.

Not simulation logic — just small utilities useful for tests, the demo
script, and (later) delivery/commentary consumers that need a quick
scoreboard without re-deriving it from raw events themselves.
"""

from app.domain.team import Team
from app.engine.events import EventType, MatchEvent
from app.engine.statistics import MatchStatistics

_GOAL_TYPES = frozenset({EventType.GOAL, EventType.PENALTY_GOAL})


def final_score(events: list[MatchEvent], team_a_id: str, team_b_id: str) -> dict[str, int]:
    """Goal count per team, derived by counting GOAL events."""
    score = {team_a_id: 0, team_b_id: 0}
    for event in events:
        if event.type in _GOAL_TYPES and event.team_id in score:
            score[event.team_id] += 1
    return score


def build_match_summary(
    events: list[MatchEvent],
    stats: MatchStatistics,
    team_a: Team,
    team_b: Team,
) -> list[str]:
    """Short evidence-based bullets explaining the result."""
    bullets: list[str] = []
    sa, sb = team_a.id, team_b.id
    ta, tb = stats.teams[sa], stats.teams[sb]

    if ta.goals > tb.goals:
        bullets.append(f"{team_a.name} converted more often ({ta.goals} vs {tb.goals}).")
    elif tb.goals > ta.goals:
        bullets.append(f"{team_b.name} converted more often ({tb.goals} vs {ta.goals}).")
    else:
        bullets.append("The sides finished level on goals.")

    if ta.shots + 5 < tb.shots:
        bullets.append(f"{team_b.name} created more shooting chances ({tb.shots} vs {ta.shots}).")
    elif tb.shots + 5 < ta.shots:
        bullets.append(f"{team_a.name} created more shooting chances ({ta.shots} vs {tb.shots}).")

    reds = [e for e in events if e.type == EventType.CARD and e.payload.get("color") == "red"]
    if reds:
        team_name = team_a.name if reds[0].team_id == sa else team_b.name
        bullets.append(f"{team_name} finished with at least one sending-off.")

    if ta.saves + tb.saves > 4:
        bullets.append("Goalkeeping played a significant part — multiple saves recorded.")

    return bullets[:6]


def player_end_states(team_a: Team, team_b: Team, stats: MatchStatistics) -> list[dict]:
    rows: list[dict] = []
    for team in (team_a, team_b):
        for player in (*team.starting_xi, *team.bench):
            ps = stats.players.get(player.id)
            rows.append(
                {
                    "player_id": player.id,
                    "team_id": team.id,
                    "name": player.name,
                    "minutes_played": ps.minutes_played if ps else 0,
                    "goals": ps.goals if ps else 0,
                    "yellow_cards": player.yellow_cards,
                    "red_cards": ps.red_cards if ps else 0,
                    "fitness_after": round(player.fitness, 3),
                    "available": player.available,
                }
            )
    return rows


def team_goals_consistent(
    events: list[MatchEvent], stats: MatchStatistics, team_a_id: str, team_b_id: str
) -> bool:
    """True when live statistics goal totals match the event log."""
    derived = final_score(events, team_a_id, team_b_id)
    return (
        derived[team_a_id] == stats.teams[team_a_id].goals
        and derived[team_b_id] == stats.teams[team_b_id].goals
    )
