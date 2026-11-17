"""Tactical pitch model: ball and player positions on a 0–100 normalized grid."""

from dataclasses import dataclass, field

from app.domain.formation import FORMATION_ANCHORS, Formation
from app.domain.player import Player
from app.domain.team import Team
from app.engine.phase import Phase

_PHASE_BALL: dict[Phase, tuple[float, float]] = {
    Phase.BUILD_UP: (25.0, 50.0),
    Phase.MIDFIELD: (50.0, 50.0),
    Phase.FINAL_THIRD: (72.0, 50.0),
    Phase.SHOT: (88.0, 50.0),
}

_MAX_STEP = 6.0


@dataclass
class PitchState:
    ball_x: float = 50.0
    ball_y: float = 50.0
    possession_team_id: str | None = None
    ball_carrier_id: str | None = None
    players: dict[str, dict[str, float]] = field(default_factory=dict)

    def to_payload(self) -> dict:
        return {
            "ball": {"x": round(self.ball_x, 1), "y": round(self.ball_y, 1)},
            "possession_team_id": self.possession_team_id,
            "ball_carrier_id": self.ball_carrier_id,
            "players": {
                pid: {"x": round(pos["x"], 1), "y": round(pos["y"], 1)}
                for pid, pos in self.players.items()
            },
        }


class PitchModel:
    """Updates positions from formation anchors and possession phase."""

    def __init__(
        self,
        team_a: Team,
        team_b: Team,
        home_attacks_high_x: bool = True,
    ) -> None:
        self._team_a = team_a
        self._team_b = team_b
        self._home_attacks_high_x = home_attacks_high_x
        self.state = PitchState()
        self._init_positions()

    def _init_positions(self) -> None:
        self._place_team(self._team_a, attacking_right=self._home_attacks_high_x)
        self._place_team(self._team_b, attacking_right=not self._home_attacks_high_x)
        self.state.ball_x, self.state.ball_y = 50.0, 50.0

    def _place_team(self, team: Team, *, attacking_right: bool) -> None:
        anchors = FORMATION_ANCHORS.get(team.formation, FORMATION_ANCHORS[Formation.FOUR_THREE_THREE])
        for player, (ax, ay) in zip(team.starting_xi, anchors, strict=False):
            x, y = ax, ay
            if not attacking_right:
                x = 100.0 - x
            self.state.players[player.id] = {"x": x, "y": y}

    def team_attacks_right(self, team_id: str) -> bool:
        if team_id == self._team_a.id:
            return self._home_attacks_high_x
        return not self._home_attacks_high_x

    def reset_for_kickoff(self, possession_team_id: str) -> None:
        self.state.possession_team_id = possession_team_id
        self.state.ball_carrier_id = None
        self.state.ball_x, self.state.ball_y = 50.0, 50.0

    def place_ball(self, x: float, y: float, possession_team_id: str) -> None:
        self.state.ball_x = max(0.0, min(100.0, x))
        self.state.ball_y = max(0.0, min(100.0, y))
        self.state.possession_team_id = possession_team_id
        self.state.ball_carrier_id = None

    def after_chain(
        self,
        attacking: Team,
        defending: Team,
        last_phase: Phase | None,
        ball_carrier: Player | None,
    ) -> None:
        if last_phase is None:
            return
        bx, by = _PHASE_BALL[last_phase]
        if attacking.id == self._team_b.id:
            bx = 100.0 - bx
        self.state.ball_x, self.state.ball_y = bx, by
        self.state.possession_team_id = attacking.id
        self.state.ball_carrier_id = ball_carrier.id if ball_carrier else None

        if ball_carrier:
            self._nudge_toward(ball_carrier.id, bx, by)

        for team, attacks_high in (
            (self._team_a, attacking.id == self._team_a.id),
            (self._team_b, attacking.id == self._team_b.id),
        ):
            anchors = FORMATION_ANCHORS.get(team.formation, FORMATION_ANCHORS[Formation.FOUR_THREE_THREE])
            shift = 4.0 if (team.id == attacking.id) else -2.0
            attacking_right = (team.id == self._team_a.id and self._home_attacks_high_x) or (
                team.id == self._team_b.id and not self._home_attacks_high_x
            )
            if not attacking_right:
                shift = -shift
            for player, (ax, ay) in zip(team.starting_xi, anchors, strict=False):
                if not player.available:
                    continue
                x = ax + (shift if team.id == attacking.id else -shift * 0.5)
                y = ay
                if not attacking_right:
                    x = 100.0 - x
                x = max(0.0, min(100.0, x))
                self._nudge_toward(player.id, x, y)

    def _nudge_toward(self, player_id: str, target_x: float, target_y: float) -> None:
        if player_id not in self.state.players:
            self.state.players[player_id] = {"x": target_x, "y": target_y}
            return
        pos = self.state.players[player_id]
        dx = max(-_MAX_STEP, min(_MAX_STEP, target_x - pos["x"]))
        dy = max(-_MAX_STEP, min(_MAX_STEP, target_y - pos["y"]))
        pos["x"] += dx
        pos["y"] += dy

    def refresh_team(self, team: Team) -> None:
        """Re-seat a team's players after a formation change."""
        attacking_right = (team.id == self._team_a.id and self._home_attacks_high_x) or (
            team.id == self._team_b.id and not self._home_attacks_high_x
        )
        self._place_team(team, attacking_right=attacking_right)

    def attach(self, payload: dict) -> dict:
        payload = dict(payload)
        payload["pitch"] = self.state.to_payload()
        return payload