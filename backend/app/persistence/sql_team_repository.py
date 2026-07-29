"""SqlTeamRepository: the only code that translates between domain
Team/Player/Tactic objects and TeamModel/PlayerModel ORM rows. See
persistence/CLAUDE.md.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import selectinload

from app.domain.player import Player, PlayerAttributes, Position
from app.domain.tactic import DefensiveLine, MarkingScheme, Mentality, Pressing, Tactic, Tempo, Width
from app.domain.team import Team
from app.persistence.models import PlayerModel, TeamModel
from app.persistence.team_repository import TeamRepository


class SqlTeamRepository(TeamRepository):
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def save(self, team: Team) -> None:
        model = self._to_model(team)
        async with self._session_factory() as session:
            await session.merge(model)
            await session.commit()

    async def get(self, team_id: str) -> Team | None:
        async with self._session_factory() as session:
            model = await session.get(TeamModel, team_id, options=[selectinload(TeamModel.players)])
            return self._to_domain(model) if model else None

    async def list_all(self) -> list[Team]:
        async with self._session_factory() as session:
            result = await session.execute(select(TeamModel).options(selectinload(TeamModel.players)))
            return [self._to_domain(model) for model in result.scalars().all()]

    def _to_model(self, team: Team) -> TeamModel:
        model = TeamModel(
            id=team.id,
            name=team.name,
            mentality=team.tactic.mentality.value,
            tempo=team.tactic.tempo.value,
            pressing=team.tactic.pressing.value,
            width=team.tactic.width.value,
            defensive_line=team.tactic.defensive_line.value,
            marking_scheme=team.tactic.marking_scheme.value,
        )
        model.players = [
            *(self._player_to_model(p, is_bench=False) for p in team.starting_xi),
            *(self._player_to_model(p, is_bench=True) for p in team.bench),
        ]
        return model

    def _player_to_model(self, player: Player, is_bench: bool) -> PlayerModel:
        attrs = player.attributes
        return PlayerModel(
            id=player.id,
            is_bench=is_bench,
            name=player.name,
            position=player.position.value,
            pace=attrs.pace, dribbling=attrs.dribbling, passing=attrs.passing, vision=attrs.vision,
            shooting=attrs.shooting, tackling=attrs.tackling, marking=attrs.marking, strength=attrs.strength,
            positioning=attrs.positioning, aggression=attrs.aggression, composure=attrs.composure,
            stamina=attrs.stamina, flair=attrs.flair, reflexes=attrs.reflexes, handling=attrs.handling,
            gk_positioning=attrs.gk_positioning,
        )

    def _to_domain(self, model: TeamModel) -> Team:
        starting_xi = [self._player_to_domain(p) for p in model.players if not p.is_bench]
        bench = [self._player_to_domain(p) for p in model.players if p.is_bench]
        tactic = Tactic(
            mentality=Mentality(model.mentality),
            tempo=Tempo(model.tempo),
            pressing=Pressing(model.pressing),
            width=Width(model.width),
            defensive_line=DefensiveLine(model.defensive_line),
            marking_scheme=MarkingScheme(model.marking_scheme),
        )
        return Team(id=model.id, name=model.name, starting_xi=starting_xi, bench=bench, tactic=tactic)

    def _player_to_domain(self, model: PlayerModel) -> Player:
        return Player(
            id=model.id,
            name=model.name,
            position=Position(model.position),
            attributes=PlayerAttributes(
                pace=model.pace, dribbling=model.dribbling, passing=model.passing, vision=model.vision,
                shooting=model.shooting, tackling=model.tackling, marking=model.marking, strength=model.strength,
                positioning=model.positioning, aggression=model.aggression, composure=model.composure,
                stamina=model.stamina, flair=model.flair, reflexes=model.reflexes, handling=model.handling,
                gk_positioning=model.gk_positioning,
            ),
        )
