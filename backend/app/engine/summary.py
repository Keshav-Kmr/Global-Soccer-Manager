"""Read-only helpers for interpreting a MatchEvent stream.

Not simulation logic — just small utilities useful for tests, the demo
script, and (later) delivery/commentary consumers that need a quick
scoreboard without re-deriving it from raw events themselves.
"""

from app.engine.events import EventType, MatchEvent


def final_score(events: list[MatchEvent], team_a_id: str, team_b_id: str) -> dict[str, int]:
    """Goal count per team, derived by counting GOAL events."""
    score = {team_a_id: 0, team_b_id: 0}
    for event in events:
        if event.type == EventType.GOAL and event.team_id in score:
            score[event.team_id] += 1
    return score
