"""MatchService: owns match session lifecycle. Routes call into this;
the engine is only ever invoked from here, never from a route directly."""

import asyncio
import random
import uuid

from app.commentary.generator import CommentaryGenerator
from app.domain.formation import Formation
from app.domain.match_context import MatchContext
from app.domain.player import Player
from app.domain.tactic import Tactic
from app.domain.team import Team
from app.delivery.schemas import MatchEventMessage
from app.delivery.services.match_session import MatchRunMode, MatchSession
from app.delivery.services.pacer import Pacer
from app.engine.auto_substitution import MAX_SUBSTITUTIONS
from app.engine.clock import MINUTES_PER_CHAIN
from app.engine.events import MatchEvent
from app.engine.match import Match
from app.engine.match_snapshot import export_snapshot, restore_snapshot
from app.engine.summary import build_match_summary, final_score, player_end_states
from app.persistence.match_result_repository import MatchResult, MatchResultRepository
from app.persistence.repository import MatchRepository


class MatchServiceError(Exception):
    """Base error for illegal match operations."""


class MatchNotFoundError(MatchServiceError):
    pass


class MatchFinishedError(MatchServiceError):
    pass


class MatchPausedError(MatchServiceError):
    pass


class InvalidMatchCommandError(MatchServiceError):
    pass


class MatchService:
    def __init__(
        self,
        repository: MatchRepository,
        pacer: Pacer | None = None,
        match_result_repository: MatchResultRepository | None = None,
    ) -> None:
        self._repository = repository
        self._pacer = pacer or Pacer()
        self._commentary = CommentaryGenerator()
        self._match_result_repository = match_result_repository
        self._sessions: dict[str, MatchSession] = {}

    async def start_match(
        self,
        team_a: Team,
        team_b: Team,
        seed: int | None,
        context: MatchContext,
        *,
        controlled: bool = False,
    ) -> str:
        match_id = str(uuid.uuid4())
        resolved_seed = seed if seed is not None else random.randint(0, 2**31 - 1)
        match = Match(team_a, team_b, resolved_seed, context)
        roster = self._build_roster(team_a, team_b)
        commentary_rng = random.Random(match.seed)
        mode = MatchRunMode.CONTROLLED if controlled else MatchRunMode.AUTO

        self._repository.create(match_id)
        session = MatchSession(
            match_id=match_id,
            match=match,
            team_a=team_a,
            team_b=team_b,
            roster=roster,
            commentary_rng=commentary_rng,
            mode=mode,
        )
        self._sessions[match_id] = session
        self._flush_new_events(session)

        if mode == MatchRunMode.AUTO:
            asyncio.create_task(self._run_auto(match_id))
        return match_id

    async def _run_auto(self, match_id: str) -> None:
        session = self._require_session(match_id)
        match = session.match
        while not match.finished:
            if match.paused:
                await asyncio.sleep(0.05)
                continue
            match.play_next_chain()
            self._flush_new_events(session)
            await self._pacer.wait(MINUTES_PER_CHAIN)
        await self._finalize(session)

    def _flush_new_events(self, session: MatchSession) -> None:
        match = session.match
        while session.wired_event_count < len(match.events):
            event = match.events[session.wired_event_count]
            message = self._to_message(event, session.roster, session.commentary_rng, session.wired_event_count)
            wire_event = message.model_dump()
            session.wire_log.append(wire_event)
            self._repository.append_event(session.match_id, wire_event)
            session.wired_event_count += 1

    def _rebuild_wire_log(self, session: MatchSession) -> None:
        session.wire_log.clear()
        session.wired_event_count = 0
        self._flush_new_events(session)
        self._repository.replace_events(session.match_id, list(session.wire_log))

    async def _finalize(self, session: MatchSession) -> None:
        self._repository.mark_finished(session.match_id)
        if self._match_result_repository is None:
            return
        match = session.match
        score = final_score(match.events, session.team_a.id, session.team_b.id)
        await self._match_result_repository.save(
            MatchResult(
                match_id=session.match_id,
                team_a_id=session.team_a.id,
                team_a_name=session.team_a.name,
                team_b_id=session.team_b.id,
                team_b_name=session.team_b.name,
                score_a=score[session.team_a.id],
                score_b=score[session.team_b.id],
                seed=match.seed,
                events=session.wire_log,
                statistics=match.statistics.to_dict(),
                summary=build_match_summary(match.events, match.statistics, session.team_a, session.team_b),
                player_states=player_end_states(session.team_a, session.team_b, match.statistics),
            )
        )

    def get_state(self, match_id: str) -> dict:
        session = self._require_session(match_id)
        match = session.match
        score = {
            session.team_a.id: match.statistics.teams[session.team_a.id].goals,
            session.team_b.id: match.statistics.teams[session.team_b.id].goals,
        }
        return {
            "match_id": match_id,
            "mode": session.mode.value,
            "minute": match.minute,
            "paused": match.paused,
            "finished": match.finished,
            "score": score,
            "team_a_id": session.team_a.id,
            "team_b_id": session.team_b.id,
            "seed": match.seed,
            "clock": match.clock_state(),
        }

    async def advance(
        self,
        match_id: str,
        steps: int = 1,
        *,
        target_minute: int | None = None,
        next_key_event: bool = False,
        until_finished: bool = False,
    ) -> dict:
        session = self._require_session(match_id)
        if session.mode != MatchRunMode.CONTROLLED:
            raise InvalidMatchCommandError("advance is only available for controlled matches")
        match = session.match
        if match.finished:
            raise MatchFinishedError("match is already finished")
        if match.paused:
            raise MatchPausedError("match is paused")

        advanced = 0
        if until_finished:
            while not match.finished:
                match.play_next_chain()
                advanced += 1
        elif target_minute is not None:
            advanced = match.play_to_minute(target_minute)
        elif next_key_event:
            advanced = match.play_to_next_key_event()
        else:
            if steps < 1:
                raise InvalidMatchCommandError("steps must be at least 1")
            for _ in range(steps):
                if match.finished:
                    break
                match.play_next_chain()
                advanced += 1

        self._flush_new_events(session)
        if match.finished:
            await self._finalize(session)

        return {"advanced_chains": advanced, "finished": match.finished, "minute": match.minute}

    def export_match_snapshot(self, match_id: str) -> dict:
        session = self._require_session(match_id)
        if session.match.finished:
            raise MatchFinishedError("cannot snapshot a finished match")
        return export_snapshot(session.match)

    def restore_match_snapshot(self, match_id: str, snapshot: dict) -> None:
        session = self._require_session(match_id)
        if session.match.finished:
            raise MatchFinishedError("cannot restore into a finished match")
        if snapshot.get("version") != 1:
            raise InvalidMatchCommandError("unsupported snapshot version")
        restore_snapshot(session.match, snapshot)
        self._rebuild_wire_log(session)

    def pause(self, match_id: str) -> None:
        session = self._require_session(match_id)
        if session.match.finished:
            raise MatchFinishedError("match is already finished")
        session.match.set_paused(True)

    def resume(self, match_id: str) -> None:
        session = self._require_session(match_id)
        if session.match.finished:
            raise MatchFinishedError("match is already finished")
        session.match.set_paused(False)

    def change_tactic(self, match_id: str, team_id: str, tactic: Tactic) -> None:
        session = self._require_session(match_id)
        match = session.match
        if match.finished:
            raise MatchFinishedError("match is already finished")
        team = match.team_by_id(team_id)
        if team is None:
            raise InvalidMatchCommandError(f"unknown team id {team_id!r}")
        match.change_tactic(team, tactic)
        self._flush_new_events(session)

    def change_formation(self, match_id: str, team_id: str, formation: Formation) -> None:
        session = self._require_session(match_id)
        match = session.match
        if match.finished:
            raise MatchFinishedError("match is already finished")
        team = match.team_by_id(team_id)
        if team is None:
            raise InvalidMatchCommandError(f"unknown team id {team_id!r}")
        try:
            match.change_formation(team, formation)
        except ValueError as exc:
            raise InvalidMatchCommandError(str(exc)) from exc
        self._flush_new_events(session)

    def substitute(self, match_id: str, team_id: str, player_out_id: str, player_in_id: str) -> None:
        session = self._require_session(match_id)
        match = session.match
        if match.finished:
            raise MatchFinishedError("match is already finished")
        team = match.team_by_id(team_id)
        if team is None:
            raise InvalidMatchCommandError(f"unknown team id {team_id!r}")
        if team.substitutions_used >= MAX_SUBSTITUTIONS:
            raise InvalidMatchCommandError(f"substitution limit ({MAX_SUBSTITUTIONS}) reached")

        try:
            player_out = next(p for p in team.starting_xi if p.id == player_out_id)
        except StopIteration as exc:
            raise InvalidMatchCommandError("player_out is not in the starting XI") from exc
        try:
            player_in = next(p for p in team.bench if p.id == player_in_id)
        except StopIteration as exc:
            raise InvalidMatchCommandError("player_in is not on the bench") from exc
        if not player_out.available:
            raise InvalidMatchCommandError("player_out is not available")

        match.substitute(team, player_out, player_in)
        team.bench.remove(player_in)
        team.bench.append(player_out)
        team.substitutions_used += 1
        session.roster[player_in.id] = player_in
        self._flush_new_events(session)

    def _to_message(
        self,
        event: MatchEvent,
        roster: dict[str, Player],
        commentary_rng: random.Random,
        index: int,
    ) -> MatchEventMessage:
        return MatchEventMessage(
            index=index,
            minute=event.minute,
            type=event.type.value,
            team=event.team_id,
            players=list(event.player_ids),
            payload=event.payload,
            commentary=self._commentary.describe(event, roster, commentary_rng),
        )

    def _build_roster(self, team_a: Team, team_b: Team) -> dict[str, Player]:
        players = [*team_a.starting_xi, *team_a.bench, *team_b.starting_xi, *team_b.bench]
        return {p.id: p for p in players}

    def _require_session(self, match_id: str) -> MatchSession:
        if match_id not in self._sessions:
            raise MatchNotFoundError(f"no live session for match id {match_id!r}")
        return self._sessions[match_id]

    def exists(self, match_id: str) -> bool:
        return self._repository.exists(match_id)

    def get_events(self, match_id: str, since_index: int = 0) -> list[dict]:
        return self._repository.get_events(match_id, since_index)

    def is_finished(self, match_id: str) -> bool:
        return self._repository.is_finished(match_id)

    def get_statistics(self, match_id: str) -> dict:
        session = self._require_session(match_id)
        return session.match.statistics.to_dict()

    async def get_result(self, match_id: str) -> MatchResult | None:
        if self._match_result_repository is None:
            return None
        return await self._match_result_repository.get(match_id)