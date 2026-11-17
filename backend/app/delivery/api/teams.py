"""FastAPI routes for team persistence — thin, per backend/CLAUDE.md."""

from fastapi import APIRouter, Depends, HTTPException, Request

from app.delivery.schemas import TeamSchema, team_from_schema, team_to_schema
from app.delivery.services.team_service import TeamService

router = APIRouter()


def get_team_service(request: Request) -> TeamService:
    return request.app.state.team_service


@router.post("/teams", response_model=TeamSchema)
async def create_team(body: TeamSchema, service: TeamService = Depends(get_team_service)) -> TeamSchema:
    await service.save(team_from_schema(body))
    return body


@router.get("/teams/{team_id}", response_model=TeamSchema)
async def get_team(team_id: str, service: TeamService = Depends(get_team_service)) -> TeamSchema:
    team = await service.get(team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="team not found")
    return team_to_schema(team)


@router.get("/teams", response_model=list[TeamSchema])
async def list_teams(service: TeamService = Depends(get_team_service)) -> list[TeamSchema]:
    teams = await service.list_all()
    return [team_to_schema(team) for team in teams]
