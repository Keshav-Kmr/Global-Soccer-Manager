"""SqlMatchResultRepository: the SQL-backed MatchResultRepository. Events
are stored as a JSON blob (`events_json`) rather than normalized rows —
they're write-once, read-whole, never queried by field, so a relational
breakdown would only add ceremony with no real benefit.
"""

import json

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.persistence.match_result_repository import MatchResult, MatchResultRepository
from app.persistence.models import MatchResultModel


class SqlMatchResultRepository(MatchResultRepository):
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def save(self, result: MatchResult) -> None:
        model = MatchResultModel(
            id=result.match_id,
            team_a_id=result.team_a_id,
            team_a_name=result.team_a_name,
            team_b_id=result.team_b_id,
            team_b_name=result.team_b_name,
            score_a=result.score_a,
            score_b=result.score_b,
            seed=result.seed,
            events_json=json.dumps(
                {
                    "events": result.events,
                    "statistics": result.statistics,
                    "summary": result.summary,
                    "player_states": result.player_states,
                }
            ),
        )
        async with self._session_factory() as session:
            await session.merge(model)
            await session.commit()

    async def get(self, match_id: str) -> MatchResult | None:
        async with self._session_factory() as session:
            model = await session.get(MatchResultModel, match_id)
            if model is None:
                return None
            raw = json.loads(model.events_json)
            if isinstance(raw, list):
                return MatchResult(
                    match_id=model.id,
                    team_a_id=model.team_a_id,
                    team_a_name=model.team_a_name,
                    team_b_id=model.team_b_id,
                    team_b_name=model.team_b_name,
                    score_a=model.score_a,
                    score_b=model.score_b,
                    seed=model.seed,
                    events=raw,
                )
            return MatchResult(
                match_id=model.id,
                team_a_id=model.team_a_id,
                team_a_name=model.team_a_name,
                team_b_id=model.team_b_id,
                team_b_name=model.team_b_name,
                score_a=model.score_a,
                score_b=model.score_b,
                seed=model.seed,
                events=raw.get("events", []),
                statistics=raw.get("statistics"),
                summary=raw.get("summary"),
                player_states=raw.get("player_states"),
            )
