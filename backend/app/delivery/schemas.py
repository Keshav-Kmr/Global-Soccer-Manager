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

from typing import Literal

from pydantic import BaseModel, Field

from app.domain.formation import Formation
from app.domain.match_context import MatchContext, Weather
from app.domain.player import Player, PlayerAttributes, Position
from enum import Enum
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
    formation: Formation = Formation.FOUR_THREE_THREE


class MatchRunModeSchema(str, Enum):
    AUTO = "auto"
    CONTROLLED = "controlled"


class CreateMatchRequest(BaseModel):
    team_a: TeamSchema
    team_b: TeamSchema
    seed: int | None = None
    weather: Weather = Weather.CLEAR
    mode: MatchRunModeSchema = MatchRunModeSchema.AUTO


class CreateMatchResponse(BaseModel):
    match_id: str


class MatchStateSchema(BaseModel):
    match_id: str
    mode: str
    minute: int
    paused: bool
    finished: bool
    score: dict[str, int]
    team_a_id: str
    team_b_id: str
    seed: int
    clock: dict | None = None


class AdvanceMatchRequest(BaseModel):
    steps: int = Field(default=1, ge=1, le=500)
    target_minute: int | None = Field(default=None, ge=0, le=120)
    next_key_event: bool = False
    until_finished: bool = False


class AdvanceMatchResponse(BaseModel):
    advanced_chains: int
    finished: bool
    minute: int


class ChangeTacticRequest(BaseModel):
    team_id: str
    tactic: TacticSchema


class ChangeFormationRequest(BaseModel):
    team_id: str
    formation: Formation


class SubstitutionRequest(BaseModel):
    team_id: str
    player_out_id: str
    player_in_id: str


class MatchStatisticsSchema(BaseModel):
    teams: dict
    players: dict


class MatchEventMessage(BaseModel):
    """The WebSocket wire format — see delivery/CLAUDE.md. Deliberately
    uses `team`/`players`, not the engine's `team_id`/`player_ids`: this
    is the public contract, free to diverge from internal naming."""

    index: int
    minute: int
    type: str
    team: str | None
    players: list[str]
    payload: dict
    commentary: str


class SnapshotResponse(BaseModel):
    snapshot: dict


class RestoreSnapshotRequest(BaseModel):
    snapshot: dict


class ReplayActionSchema(BaseModel):
    at_minute: int = Field(ge=0, le=130)
    action: Literal["tactic_change", "formation_change", "substitution"]
    team_id: str
    tactic: TacticSchema | None = None
    formation: Formation | None = None
    player_out_id: str | None = None
    player_in_id: str | None = None


class ReplayMatchRequest(BaseModel):
    team_a: TeamSchema
    team_b: TeamSchema
    seed: int
    weather: Weather = Weather.CLEAR
    actions: list[ReplayActionSchema] = Field(default_factory=list)
    include_commentary: bool = True


class ReplayMatchResponse(BaseModel):
    seed: int
    score: dict[str, int]
    team_a_id: str
    team_b_id: str
    score_a: int
    score_b: int
    event_count: int
    events: list[dict]
    statistics: dict
    summary: list[str]
    player_states: list[dict]


class VerifyReplayResponse(BaseModel):
    match_id: str
    found_stored_result: bool
    score_matches: bool
    event_signature_matches: bool
    stored_score: dict[str, int]
    replay_score: dict[str, int]
    stored_event_count: int
    replay_event_count: int


class MatchResultSchema(BaseModel):
    """The durable, post-match record — see persistence/match_result_repository.py."""

    match_id: str
    team_a_id: str
    team_a_name: str
    team_b_id: str
    team_b_name: str
    score_a: int
    score_b: int
    seed: int
    events: list[dict]
    statistics: dict | None = None
    summary: list[str] | None = None
    player_states: list[dict] | None = None


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


def _player_to_schema(player: Player) -> PlayerSchema:
    attrs = player.attributes
    return PlayerSchema(
        id=player.id,
        name=player.name,
        position=player.position,
        attributes=PlayerAttributesSchema(
            pace=attrs.pace,
            dribbling=attrs.dribbling,
            passing=attrs.passing,
            vision=attrs.vision,
            shooting=attrs.shooting,
            tackling=attrs.tackling,
            marking=attrs.marking,
            strength=attrs.strength,
            positioning=attrs.positioning,
            aggression=attrs.aggression,
            composure=attrs.composure,
            stamina=attrs.stamina,
            flair=attrs.flair,
            reflexes=attrs.reflexes,
            handling=attrs.handling,
            gk_positioning=attrs.gk_positioning,
        ),
    )


def team_to_schema(team: Team) -> TeamSchema:
    return TeamSchema(
        id=team.id,
        name=team.name,
        starting_xi=[_player_to_schema(p) for p in team.starting_xi],
        bench=[_player_to_schema(p) for p in team.bench],
        tactic=TacticSchema(
            mentality=team.tactic.mentality,
            tempo=team.tactic.tempo,
            pressing=team.tactic.pressing,
            width=team.tactic.width,
            defensive_line=team.tactic.defensive_line,
            marking_scheme=team.tactic.marking_scheme,
        ),
        formation=team.formation,
    )


def team_from_schema(schema: TeamSchema) -> Team:
    return Team(
        id=schema.id,
        name=schema.name,
        starting_xi=[_player_from_schema(p) for p in schema.starting_xi],
        bench=[_player_from_schema(p) for p in schema.bench],
        tactic=_tactic_from_schema(schema.tactic),
        formation=schema.formation,
    )


def context_from_request(request: CreateMatchRequest) -> MatchContext:
    return MatchContext(weather=request.weather)


def validate_match_lineups(team_a: Team, team_b: Team) -> None:
    """Cross-team and duplicate-ID checks beyond formation slot validation."""
    if team_a.id == team_b.id:
        raise ValueError("team_a and team_b must have distinct ids")

    for label, team in (("team_a", team_a), ("team_b", team_b)):
        roster_ids = [p.id for p in (*team.starting_xi, *team.bench)]
        if len(roster_ids) != len(set(roster_ids)):
            raise ValueError(f"{label} has duplicate player ids")
        starting = {p.id for p in team.starting_xi}
        bench = {p.id for p in team.bench}
        if starting & bench:
            raise ValueError(f"{label} has a player in both starting_xi and bench")

    ids_a = {p.id for p in (*team_a.starting_xi, *team_a.bench)}
    ids_b = {p.id for p in (*team_b.starting_xi, *team_b.bench)}
    overlap = ids_a & ids_b
    if overlap:
        raise ValueError(f"player id(s) appear on both teams: {sorted(overlap)}")
