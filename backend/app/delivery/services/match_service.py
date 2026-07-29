"""MatchService: owns match session lifecycle. Routes call into this;
the engine is only ever invoked from here, never from a route directly
(backend/CLAUDE.md, delivery/CLAUDE.md).

A match is simulated once, server-side, in a background asyncio task,
regardless of how many clients end up watching — see delivery/CLAUDE.md's
"session lifecycle". `MatchService` depends on the `MatchRepository`
interface, never a concrete store, so swapping in a real database later
doesn't touch this class.
"""

import asyncio
import random
import uuid

from app.commentary.generator import CommentaryGenerator
from app.domain.match_context import MatchContext
from app.domain.player import Player
from app.domain.team import Team
from app.delivery.schemas import MatchEventMessage
from app.delivery.services.pacer import Pacer
from app.engine.events import MatchEvent
from app.engine.match import MINUTES_PER_CHAIN, Match
from app.engine.summary import final_score
from app.persistence.match_result_repository import MatchResult, MatchResultRepository
from app.persistence.repository import MatchRepository


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
        # Optional: the live in-memory session (above) is all that's
        # needed for streaming; this is only for the match to still be
        # look-up-able after the process restarts (persistence/CLAUDE.md).
        self._match_result_repository = match_result_repository

    async def start_match(
        self, team_a: Team, team_b: Team, seed: int | None, context: MatchContext
    ) -> str:
        """Creates the match session and kicks off its simulation in the
        background immediately — does not wait for any viewer to connect."""
        match_id = str(uuid.uuid4())
        resolved_seed = seed if seed is not None else random.randint(0, 2**31 - 1)
        match = Match(team_a, team_b, resolved_seed, context)
        roster = self._build_roster(team_a, team_b)
        commentary_rng = random.Random(match.seed)

        self._repository.create(match_id)
        asyncio.create_task(self._run(match_id, match, team_a, team_b, roster, commentary_rng))
        return match_id

    async def _run(
        self,
        match_id: str,
        match: Match,
        team_a: Team,
        team_b: Team,
        roster: dict[str, Player],
        commentary_rng: random.Random,
    ) -> None:
        # Read from match.events (Match's own running log), not the
        # ChainResult play_next_chain() returns: KICKOFF is appended in
        # Match.__init__, before any chain runs, and FULL_TIME is appended
        # inside play_next_chain() itself, separately from the ChainResult
        # — relying on the ChainResult alone would silently drop both.
        sent = 0
        wire_events: list[dict] = []
        while not match.finished:
            match.play_next_chain()
            for event in match.events[sent:]:
                message = self._to_message(event, roster, commentary_rng)
                wire_event = message.model_dump()
                wire_events.append(wire_event)
                self._repository.append_event(match_id, wire_event)
            sent = len(match.events)
            await self._pacer.wait(MINUTES_PER_CHAIN)
        self._repository.mark_finished(match_id)

        if self._match_result_repository is not None:
            score = final_score(match.events, team_a.id, team_b.id)
            await self._match_result_repository.save(
                MatchResult(
                    match_id=match_id,
                    team_a_id=team_a.id,
                    team_a_name=team_a.name,
                    team_b_id=team_b.id,
                    team_b_name=team_b.name,
                    score_a=score[team_a.id],
                    score_b=score[team_b.id],
                    seed=match.seed,
                    events=wire_events,
                )
            )

    def _to_message(
        self, event: MatchEvent, roster: dict[str, Player], commentary_rng: random.Random
    ) -> MatchEventMessage:
        return MatchEventMessage(
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

    def exists(self, match_id: str) -> bool:
        return self._repository.exists(match_id)

    def get_events(self, match_id: str, since_index: int = 0) -> list[dict]:
        return self._repository.get_events(match_id, since_index)

    def is_finished(self, match_id: str) -> bool:
        return self._repository.is_finished(match_id)

    async def get_result(self, match_id: str) -> MatchResult | None:
        """The durable record, if this service was configured with a
        MatchResultRepository and the match has finished — survives a
        process restart, unlike the live in-memory session above."""
        if self._match_result_repository is None:
            return None
        return await self._match_result_repository.get(match_id)
