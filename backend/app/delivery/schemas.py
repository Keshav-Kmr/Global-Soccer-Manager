"""Pydantic models for REST request/response bodies and the WebSocket wire
format. Kept separate from app/domain (backend/CLAUDE.md): the domain
models describe the simulation's internal world and can evolve freely;
these describe the wire contract API clients depend on. Plain value enums
(Position, Mentality, ...) are reused directly from domain — they're just
fixed string vocabularies, not behavior, so duplicating them would only
add drift risk with no benefit.

`team_from_schema()` converts an inbound request into the domain objects
the engine actually runs on; nothing in engine/ or domain/ ever imports
from here.
"""

from pydantic import BaseModel, Field

from app.domain.match_context import MatchContext, Weather
from app.domain.player import Player, PlayerAttributes, Position
from app.domain.tactic import DefensiveLine, MarkingScheme, Mentality, Pressing, Tactic, Tempo, Width
from app.domain.team import Team


class PlayerAttributesSchema(BaseModel):
    pace: int
    dribbling: int
    passing: int
    vision: int
    shooting: int
    tackling: int
    marking: int
    strength: int
    positioning: int
    aggression: int
    composure: int
    stamina: int
    flair: int
    reflexes: int = 1
    handling: int = 1
    gk_positioning: int = 1


class PlayerSchema(BaseModel):
    id: str
    name: str
    position: Position
    attributes: PlayerAttributesSchema


class TacticSchema(BaseModel):
    mentality: Mentality = Mentality.BALANCED
    tempo: Tempo = Tempo.NORMAL
    pressing: Pressing = Pressing.MEDIUM
    width: Width = Width.NORMAL
    defensive_line: DefensiveLine = DefensiveLine.NORMAL
    marking_scheme: MarkingScheme = MarkingScheme.ZONAL


class TeamSchema(BaseModel):
    id: str
    name: str
    starting_xi: list[PlayerSchema] = Field(min_length=11, max_length=11)
    bench: list[PlayerSchema] = []
    tactic: TacticSchema = TacticSchema()


class CreateMatchRequest(BaseModel):
    team_a: TeamSchema
    team_b: TeamSchema
    seed: int | None = None
    weather: Weather = Weather.CLEAR


class CreateMatchResponse(BaseModel):
    match_id: str


class MatchEventMessage(BaseModel):
    """The WebSocket wire format — see delivery/CLAUDE.md. Deliberately
    uses `team`/`players`, not the engine's `team_id`/`player_ids`: this
    is the public contract, free to diverge from internal naming."""

    minute: int
    type: str
    team: str | None
    players: list[str]
    payload: dict
    commentary: str


def _player_from_schema(schema: PlayerSchema) -> Player:
    return Player(
        id=schema.id,
        name=schema.name,
        position=schema.position,
        attributes=PlayerAttributes(**schema.attributes.model_dump()),
    )


def _tactic_from_schema(schema: TacticSchema) -> Tactic:
    return Tactic(
        mentality=schema.mentality,
        tempo=schema.tempo,
        pressing=schema.pressing,
        width=schema.width,
        defensive_line=schema.defensive_line,
        marking_scheme=schema.marking_scheme,
    )


def team_from_schema(schema: TeamSchema) -> Team:
    return Team(
        id=schema.id,
        name=schema.name,
        starting_xi=[_player_from_schema(p) for p in schema.starting_xi],
        bench=[_player_from_schema(p) for p in schema.bench],
        tactic=_tactic_from_schema(schema.tactic),
    )


def context_from_request(request: CreateMatchRequest) -> MatchContext:
    return MatchContext(weather=request.weather)
