"""Match statistics accumulated from events — not fabricated at full time."""

from dataclasses import dataclass, field

from app.domain.player import Player
from app.domain.team import Team
from app.engine.events import EventType, MatchEvent


@dataclass
class PlayerStatistics:
    minutes_played: int = 0
    goals: int = 0
    shots: int = 0
    shots_on_target: int = 0
    fouls_committed: int = 0
    yellow_cards: int = 0
    red_cards: int = 0


@dataclass
class TeamStatistics:
    goals: int = 0
    shots: int = 0
    shots_on_target: int = 0
    fouls: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    possession_chains: int = 0
    passes_completed: int = 0
    passes_attempted: int = 0
    offsides: int = 0
    penalties_awarded: int = 0
    saves: int = 0
    tackles: int = 0
    blocked_shots: int = 0
    shots_off_target: int = 0

    def pass_completion_percentage(self) -> float:
        if self.passes_attempted == 0:
            return 0.0
        return round(100.0 * self.passes_completed / self.passes_attempted, 1)


class MatchStatistics:
    def __init__(self, team_a_id: str, team_b_id: str) -> None:
        self.team_a_id = team_a_id
        self.team_b_id = team_b_id
        self.teams: dict[str, TeamStatistics] = {
            team_a_id: TeamStatistics(),
            team_b_id: TeamStatistics(),
        }
        self.players: dict[str, PlayerStatistics] = {}
        self._on_pitch: dict[str, set[str]] = {team_a_id: set(), team_b_id: set()}
        self._last_minute = 0

    def register_lineups(self, team_a: Team, team_b: Team) -> None:
        for team in (team_a, team_b):
            for player in team.starting_xi:
                self._on_pitch[team.id].add(player.id)
                self.players.setdefault(player.id, PlayerStatistics())

    def on_minute_advanced(self, minute: int) -> None:
        if minute <= self._last_minute:
            return
        delta = minute - self._last_minute
        self._last_minute = minute
        for player_ids in self._on_pitch.values():
            for pid in player_ids:
                self.players.setdefault(pid, PlayerStatistics()).minutes_played += delta

    def substitution(self, team_id: str, player_out_id: str, player_in_id: str) -> None:
        self._on_pitch.setdefault(team_id, set()).discard(player_out_id)
        self._on_pitch.setdefault(team_id, set()).add(player_in_id)
        self.players.setdefault(player_in_id, PlayerStatistics())

    def possession_chain(self, attacking_team_id: str) -> None:
        self.teams[attacking_team_id].possession_chains += 1

    def apply_event(self, event: MatchEvent) -> None:
        if event.type == EventType.SUBSTITUTION and len(event.player_ids) >= 2 and event.team_id:
            self.substitution(event.team_id, event.player_ids[0], event.player_ids[1])
            return

        if event.type == EventType.PENALTY_GOAL and event.team_id:
            self.teams[event.team_id].goals += 1
            self.teams[event.team_id].penalties_awarded += 1
            if event.player_ids:
                p = self.players.setdefault(event.player_ids[0], PlayerStatistics())
                p.goals += 1
            return

        if event.type == EventType.PENALTY_AWARDED and event.team_id:
            self.teams[event.team_id].penalties_awarded += 1
            return

        if event.type == EventType.PENALTY_SAVE and event.team_id:
            self.teams[event.team_id].saves += 1
            return

        if event.type == EventType.OFFSIDE and event.team_id:
            self.teams[event.team_id].offsides += 1
            return

        if event.type == EventType.GOAL and event.team_id:
            self.teams[event.team_id].goals += 1
            self.teams[event.team_id].shots += 1
            self.teams[event.team_id].shots_on_target += 1
            if event.player_ids:
                p = self.players.setdefault(event.player_ids[0], PlayerStatistics())
                p.goals += 1
                p.shots += 1
                p.shots_on_target += 1
            return

        if event.type == EventType.POSSESSION_PROGRESS and event.team_id:
            self.teams[event.team_id].passes_completed += 1
            self.teams[event.team_id].passes_attempted += 1
            return

        if event.type == EventType.TURNOVER and event.team_id:
            self.teams[event.team_id].passes_attempted += 1
            defending = self.team_b_id if event.team_id == self.team_a_id else self.team_a_id
            self.teams[defending].tackles += 1
            return

        if event.type == EventType.SHOT and event.team_id:
            self.teams[event.team_id].shots += 1
            if event.player_ids:
                self.players.setdefault(event.player_ids[0], PlayerStatistics()).shots += 1
            return

        if event.type == EventType.BLOCK and event.team_id:
            defending = self.team_b_id if event.team_id == self.team_a_id else self.team_a_id
            self.teams[defending].blocked_shots += 1
            self.teams[event.team_id].shots_on_target += 1
            return

        if event.type == EventType.OFF_TARGET and event.team_id:
            self.teams[event.team_id].shots_off_target += 1
            return

        if event.type in (EventType.SAVE,) and event.team_id:
            defending = self.team_b_id if event.team_id == self.team_a_id else self.team_a_id
            self.teams[defending].saves += 1
            self.teams[event.team_id].shots_on_target += 1
            if event.player_ids:
                shooter = event.player_ids[0]
                self.players.setdefault(shooter, PlayerStatistics()).shots_on_target += 1
            return

        if event.type == EventType.FOUL and event.team_id:
            self.teams[event.team_id].fouls += 1
            if event.player_ids:
                self.players.setdefault(event.player_ids[0], PlayerStatistics()).fouls_committed += 1
            return

        if event.type == EventType.CARD and event.team_id:
            color = event.payload.get("color", "yellow")
            if color == "yellow":
                self.teams[event.team_id].yellow_cards += 1
                if event.player_ids:
                    self.players.setdefault(event.player_ids[0], PlayerStatistics()).yellow_cards += 1
            elif color == "red":
                self.teams[event.team_id].red_cards += 1
                if event.player_ids:
                    self.players.setdefault(event.player_ids[0], PlayerStatistics()).red_cards += 1

    def possession_percentage(self, team_id: str) -> float:
        total = sum(t.possession_chains for t in self.teams.values())
        if total == 0:
            return 50.0
        return round(100.0 * self.teams[team_id].possession_chains / total, 1)

    def to_dict(self) -> dict:
        return {
            "teams": {
                tid: {
                    "goals": ts.goals,
                    "shots": ts.shots,
                    "shots_on_target": ts.shots_on_target,
                    "fouls": ts.fouls,
                    "yellow_cards": ts.yellow_cards,
                    "red_cards": ts.red_cards,
                    "possession_pct": self.possession_percentage(tid),
                    "passes_completed": ts.passes_completed,
                    "passes_attempted": ts.passes_attempted,
                    "pass_completion_pct": ts.pass_completion_percentage(),
                    "offsides": ts.offsides,
                    "penalties": ts.penalties_awarded,
                    "saves": ts.saves,
                    "tackles": ts.tackles,
                    "blocked_shots": ts.blocked_shots,
                    "shots_off_target": ts.shots_off_target,
                }
                for tid, ts in self.teams.items()
            },
            "players": {
                pid: {
                    "minutes_played": ps.minutes_played,
                    "goals": ps.goals,
                    "shots": ps.shots,
                    "shots_on_target": ps.shots_on_target,
                    "fouls_committed": ps.fouls_committed,
                    "yellow_cards": ps.yellow_cards,
                    "red_cards": ps.red_cards,
                }
                for pid, ps in self.players.items()
            },
        }