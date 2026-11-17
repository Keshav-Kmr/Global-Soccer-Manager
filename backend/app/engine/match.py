"""Match: a stateful, steppable simulation of one match.

MatchSimulator.simulate() (match_simulator.py) runs a match straight
through in one call — the right tool for tests, scripts, and an eventual
"give me the final result" API path. Match is the reusable primitive
underneath it, and it supports stopping *between* possession chains to
change a team's tactic or make a substitution, with the change taking
effect on the very next chain.
"""

import random

from app.domain.formation import Formation, validate_starting_xi
from app.domain.match_context import MatchContext
from app.domain.player import Player
from app.domain.tactic import Tactic
from app.domain.team import Team
from app.engine.auto_substitution import AutoSubstitution
from app.engine.clock import MINUTES_PER_CHAIN, MATCH_MINUTES, MatchClock
from app.engine.events import EventType, KEY_EVENT_TYPES, MatchEvent, _STOPPAGE_EVENT_TYPES
from app.engine.match_situation import MatchSituation
from app.engine.pitch import PitchModel
from app.engine.possession_chain import ChainResult, PossessionChainEngine
from app.engine.statistics import MatchStatistics

_REFEREE_STRICTNESS_RANGE = (0.7, 1.3)


class Match:
    def __init__(
        self,
        team_a: Team,
        team_b: Team,
        seed: int,
        context: MatchContext | None = None,
    ) -> None:
        for team in (team_a, team_b):
            if team._original_starting_xi is None:
                team._original_starting_xi = list(team.starting_xi)
                team._original_bench = list(team.bench)
            else:
                team.starting_xi = list(team._original_starting_xi)
                team.bench = list(team._original_bench)
            team.substitutions_used = 0

        for player in (*team_a.starting_xi, *team_a.bench, *team_b.starting_xi, *team_b.bench):
            player.fitness = 1.0
            player.yellow_cards = 0
            player.available = True

        self.team_a = team_a
        self.team_b = team_b
        self._auto_substitution = AutoSubstitution()
        self.seed = seed
        self._clock = MatchClock()
        self._pitch = PitchModel(team_a, team_b)
        self._pitch.reset_for_kickoff(team_a.id)
        self.statistics = MatchStatistics(team_a.id, team_b.id)
        self.statistics.register_lineups(team_a, team_b)
        self.events: list[MatchEvent] = []

        kickoff = MatchEvent(
            minute=0,
            type=EventType.KICKOFF,
            team_id=team_a.id,
            payload=self._pitch.attach({}),
        )
        self.events.append(kickoff)

        self._paused = False
        self._rng = random.Random(seed)
        self._chain_engine = PossessionChainEngine()
        self._possession, self._other = team_a, team_b
        self._situation = MatchSituation(
            home_team_id=team_a.id,
            context=context or MatchContext(),
            referee_strictness=self._rng.uniform(*_REFEREE_STRICTNESS_RANGE),
        )

    @property
    def minute(self) -> int:
        return self._clock.minute

    @property
    def finished(self) -> bool:
        return self._clock.is_finished()

    def play_next_chain(self) -> ChainResult:
        """Advances the match by one possession chain."""
        if self.finished:
            raise RuntimeError("match is already finished")

        self._clock.advance_chain()
        self.statistics.on_minute_advanced(self._clock.minute)
        self.statistics.possession_chain(self._possession.id)

        result = self._chain_engine.run(
            self._clock.minute,
            self._possession,
            self._other,
            self._rng,
            self._situation,
            pitch_state=self._pitch.state,
            attacks_right=self._pitch.team_attacks_right(self._possession.id),
        )
        self._commit_chain_events(result)
        self._handle_auto_substitutions(result)

        carrier = self._player_by_id(result.ball_carrier_id)
        self._pitch.after_chain(self._possession, self._other, result.last_phase, carrier)

        if not result.possession_retained:
            self._possession, self._other = self._other, self._possession
            self._pitch.state.possession_team_id = self._possession.id

        if self._clock.should_emit_halftime():
            self._append_event(
                MatchEvent(
                    minute=self._clock.minute,
                    type=EventType.HALF_TIME,
                    team_id=None,
                    payload=self._halftime_payload(),
                )
            )
            self._clock.mark_halftime()
            self._pitch.reset_for_kickoff(self._possession.id)

        if self._clock.should_finish():
            self._append_event(
                MatchEvent(minute=self._clock.minute, type=EventType.FULL_TIME, team_id=None, payload={})
            )
            self._clock.mark_finished()
            self.statistics.on_minute_advanced(self._clock.minute)

        return result

    def _halftime_payload(self) -> dict:
        score = {
            self.team_a.id: self.statistics.teams[self.team_a.id].goals,
            self.team_b.id: self.statistics.teams[self.team_b.id].goals,
        }
        base = {"score": score, "stoppage_first_half": self._clock.first_half_stoppage}
        return self._pitch.attach(base)

    def _commit_chain_events(self, result: ChainResult) -> None:
        for event in result.events:
            self._append_event(event)

    def _append_event(self, event: MatchEvent) -> None:
        event.payload = self._pitch.attach(dict(event.payload))
        if event.type in _STOPPAGE_EVENT_TYPES:
            self._clock.record_interruption(event.type.value)
        self.statistics.apply_event(event)
        self.events.append(event)

    def _player_by_id(self, player_id: str | None) -> Player | None:
        if not player_id:
            return None
        for player in (*self.team_a.starting_xi, *self.team_b.starting_xi):
            if player.id == player_id:
                return player
        return None

    def _handle_auto_substitutions(self, result: ChainResult) -> None:
        for team in (self.team_a, self.team_b):
            for event in result.events:
                if event.type == EventType.INJURY and event.team_id == team.id:
                    injured_player = next(p for p in team.starting_xi if p.id == event.player_ids[0])
                    sub_event = self._auto_substitution.substitute_for_injury(team, self._clock.minute, injured_player)
                    if sub_event is not None:
                        self._append_event(sub_event)

            sub_event = self._auto_substitution.substitute_for_tiredness(team, self._clock.minute)
            if sub_event is not None:
                self._append_event(sub_event)

    def play_to_completion(self) -> list[MatchEvent]:
        while not self.finished:
            self.play_next_chain()
        return self.events

    def play_to_minute(self, target_minute: int, *, max_chains: int = 500) -> int:
        chains = 0
        while not self.finished and self.minute < target_minute and chains < max_chains:
            self.play_next_chain()
            chains += 1
        return chains

    def play_to_next_key_event(self, *, max_chains: int = 500) -> int:
        chains = 0
        while not self.finished and chains < max_chains:
            before = len(self.events)
            self.play_next_chain()
            chains += 1
            for event in self.events[before:]:
                if event.type in KEY_EVENT_TYPES:
                    if event.type == EventType.CARD and event.payload.get("color") != "red":
                        continue
                    return chains
            if self.finished:
                return chains
        return chains

    def clock_state(self) -> dict:
        clock = self._clock
        return {
            "period": clock.period.value,
            "first_half_stoppage": clock.first_half_stoppage,
            "second_half_stoppage": clock.second_half_stoppage,
            "display_minute": clock.minute,
            "regulation_first_half_end": 45,
            "regulation_match_end": 90,
        }

    def change_tactic(self, team: Team, tactic: Tactic) -> None:
        team.tactic = tactic
        self._append_event(
            MatchEvent(
                minute=self._clock.minute,
                type=EventType.TACTIC_CHANGE,
                team_id=team.id,
                payload={"mentality": tactic.mentality.value, "pressing": tactic.pressing.value},
            )
        )

    def substitute(self, team: Team, player_out: Player, player_in: Player) -> None:
        index = team.starting_xi.index(player_out)
        team.starting_xi[index] = player_in
        self._append_event(
            MatchEvent(
                minute=self._clock.minute,
                type=EventType.SUBSTITUTION,
                team_id=team.id,
                player_ids=[player_out.id, player_in.id],
                payload={"reason": "manual"},
            )
        )

    def change_formation(self, team: Team, formation: Formation) -> None:
        validate_starting_xi(team.starting_xi, formation)
        team.formation = formation
        self._pitch.refresh_team(team)
        self._append_event(
            MatchEvent(
                minute=self._clock.minute,
                type=EventType.FORMATION_CHANGE,
                team_id=team.id,
                payload={"formation": formation.value},
            )
        )

    @property
    def paused(self) -> bool:
        return self._paused

    def set_paused(self, value: bool) -> None:
        self._paused = value

    def team_by_id(self, team_id: str) -> Team | None:
        if team_id == self.team_a.id:
            return self.team_a
        if team_id == self.team_b.id:
            return self.team_b
        return None


__all__ = ["Match", "MATCH_MINUTES", "MINUTES_PER_CHAIN"]