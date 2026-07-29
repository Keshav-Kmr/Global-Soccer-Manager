"""HomeAdvantage: a small, constant boost for whichever team is playing at
home. Deliberately simple for v1 — a flat multiplier, not a breakdown into
crowd noise, travel fatigue, or pitch familiarity individually. Those would
be plausible refinements of this one class later, not new classes.
"""

HOME_BONUS = 1.05


class HomeAdvantage:
    def modifier(self, team_id: str, home_team_id: str) -> float:
        return HOME_BONUS if team_id == home_team_id else 1.0
