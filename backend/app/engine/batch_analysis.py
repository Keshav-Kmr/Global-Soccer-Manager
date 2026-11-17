"""Headless batch match simulation and distribution summaries."""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field

from app.domain.team import Team
from app.engine.events import MatchEvent
from app.engine.match import Match


@dataclass
class MatchSample:
    seed: int
    home_goals: int
    away_goals: int
    home_shots: int
    away_shots: int
    home_sot: int
    away_sot: int
    home_fouls: int
    away_fouls: int
    home_yellows: int
    away_yellows: int
    home_reds: int
    away_reds: int
    home_possession_pct: float
    away_possession_pct: float
    home_pass_completion_pct: float
    away_pass_completion_pct: float


@dataclass
class BatchReport:
    matches: int
    seeds: list[int] = field(default_factory=list)
    samples: list[MatchSample] = field(default_factory=list)

    @property
    def total_goals(self) -> list[float]:
        return [s.home_goals + s.away_goals for s in self.samples]

    @property
    def home_goals(self) -> list[float]:
        return [s.home_goals for s in self.samples]

    @property
    def away_goals(self) -> list[float]:
        return [s.away_goals for s in self.samples]

    def mean(self, values: list[float]) -> float:
        return statistics.mean(values) if values else 0.0

    def stdev(self, values: list[float]) -> float:
        return statistics.stdev(values) if len(values) > 1 else 0.0

    def home_win_rate(self) -> float:
        wins = sum(1 for s in self.samples if s.home_goals > s.away_goals)
        return wins / len(self.samples) if self.samples else 0.0

    def draw_rate(self) -> float:
        draws = sum(1 for s in self.samples if s.home_goals == s.away_goals)
        return draws / len(self.samples) if self.samples else 0.0

    def to_dict(self) -> dict:
        tg = self.total_goals
        shots = [s.home_shots + s.away_shots for s in self.samples]
        sot = [s.home_sot + s.away_sot for s in self.samples]
        fouls = [s.home_fouls + s.away_fouls for s in self.samples]
        yellows = [s.home_yellows + s.away_yellows + s.home_reds + s.away_reds for s in self.samples]
        home_poss = [s.home_possession_pct for s in self.samples]
        pass_pct = [
            (s.home_pass_completion_pct + s.away_pass_completion_pct) / 2 for s in self.samples
        ]
        return {
            "matches": self.matches,
            "goals_per_match": {"mean": round(self.mean(tg), 3), "stdev": round(self.stdev(tg), 3)},
            "home_goals_per_match": round(self.mean(self.home_goals), 3),
            "away_goals_per_match": round(self.mean(self.away_goals), 3),
            "home_win_rate": round(self.home_win_rate(), 3),
            "draw_rate": round(self.draw_rate(), 3),
            "shots_per_match": {"mean": round(self.mean(shots), 3), "stdev": round(self.stdev(shots), 3)},
            "shots_on_target_per_match": {"mean": round(self.mean(sot), 3), "stdev": round(self.stdev(sot), 3)},
            "fouls_per_match": {"mean": round(self.mean(fouls), 3), "stdev": round(self.stdev(fouls), 3)},
            "cards_per_match": {"mean": round(self.mean(yellows), 3), "stdev": round(self.stdev(yellows), 3)},
            "home_possession_pct_mean": round(self.mean(home_poss), 3),
            "pass_completion_pct_mean": round(self.mean(pass_pct), 3),
        }


def _sample_from_match(team_a: Team, team_b: Team, seed: int, events: list[MatchEvent], match: Match) -> MatchSample:
    stats = match.statistics.teams
    ta, tb = stats[team_a.id], stats[team_b.id]
    return MatchSample(
        seed=seed,
        home_goals=ta.goals,
        away_goals=tb.goals,
        home_shots=ta.shots,
        away_shots=tb.shots,
        home_sot=ta.shots_on_target,
        away_sot=tb.shots_on_target,
        home_fouls=ta.fouls,
        away_fouls=tb.fouls,
        home_yellows=ta.yellow_cards,
        away_yellows=tb.yellow_cards,
        home_reds=ta.red_cards,
        away_reds=tb.red_cards,
        home_possession_pct=match.statistics.possession_percentage(team_a.id),
        away_possession_pct=match.statistics.possession_percentage(team_b.id),
        home_pass_completion_pct=ta.pass_completion_percentage(),
        away_pass_completion_pct=tb.pass_completion_percentage(),
    )


def run_batch(team_a: Team, team_b: Team, *, count: int, seed_start: int = 0) -> BatchReport:
    """Simulate `count` matches with seeds seed_start .. seed_start+count-1."""
    report = BatchReport(matches=count)

    for offset in range(count):
        seed = seed_start + offset
        report.seeds.append(seed)
        match = Match(team_a, team_b, seed)
        events = match.play_to_completion()
        report.samples.append(_sample_from_match(team_a, team_b, seed, events, match))

    return report