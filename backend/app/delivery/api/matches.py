"""FastAPI routes for match creation and live streaming."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect

from app.delivery.schemas import (
    AdvanceMatchRequest,
    AdvanceMatchResponse,
    ChangeFormationRequest,
    ChangeTacticRequest,
    CreateMatchRequest,
    CreateMatchResponse,
    MatchResultSchema,
    MatchRunModeSchema,
    MatchStateSchema,
    MatchStatisticsSchema,
    ReplayMatchRequest,
    ReplayMatchResponse,
    RestoreSnapshotRequest,
    SnapshotResponse,
    SubstitutionRequest,
    VerifyReplayResponse,
    validate_match_lineups,
    _tactic_from_schema,
    context_from_request,
    team_from_schema,
)
from app.delivery.services.match_service import (
    InvalidMatchCommandError,
    MatchFinishedError,
    MatchNotFoundError,
    MatchPausedError,
    MatchService,
)

router = APIRouter()

_POLL_INTERVAL_SECONDS = 0.05
_UNKNOWN_MATCH_CLOSE_CODE = 4004


def get_match_service(request: Request) -> MatchService:
    return request.app.state.match_service


def get_match_service_ws(websocket: WebSocket) -> MatchService:
    return websocket.app.state.match_service


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, MatchNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, MatchPausedError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, MatchFinishedError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, InvalidMatchCommandError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    raise exc


@router.post("/matches", response_model=CreateMatchResponse)
async def create_match(
    body: CreateMatchRequest, service: MatchService = Depends(get_match_service)
) -> CreateMatchResponse:
    team_a = team_from_schema(body.team_a)
    team_b = team_from_schema(body.team_b)
    try:
        validate_match_lineups(team_a, team_b)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    context = context_from_request(body)
    controlled = body.mode == MatchRunModeSchema.CONTROLLED
    match_id = await service.start_match(team_a, team_b, body.seed, context, controlled=controlled)
    return CreateMatchResponse(match_id=match_id)


@router.get("/matches/{match_id}", response_model=MatchStateSchema)
async def get_match_state(match_id: str, service: MatchService = Depends(get_match_service)) -> MatchStateSchema:
    try:
        return MatchStateSchema.model_validate(service.get_state(match_id))
    except MatchNotFoundError as exc:
        raise _http_error(exc) from exc


@router.post("/matches/{match_id}/advance", response_model=AdvanceMatchResponse)
async def advance_match(
    match_id: str,
    body: AdvanceMatchRequest,
    service: MatchService = Depends(get_match_service),
) -> AdvanceMatchResponse:
    try:
        result = await service.advance(
            match_id,
            steps=body.steps,
            target_minute=body.target_minute,
            next_key_event=body.next_key_event,
            until_finished=body.until_finished,
        )
        return AdvanceMatchResponse.model_validate(result)
    except (MatchNotFoundError, MatchPausedError, MatchFinishedError, InvalidMatchCommandError) as exc:
        raise _http_error(exc) from exc


@router.post("/matches/{match_id}/pause")
async def pause_match(match_id: str, service: MatchService = Depends(get_match_service)) -> dict:
    try:
        service.pause(match_id)
        return {"paused": True}
    except (MatchNotFoundError, MatchFinishedError) as exc:
        raise _http_error(exc) from exc


@router.post("/matches/{match_id}/resume")
async def resume_match(match_id: str, service: MatchService = Depends(get_match_service)) -> dict:
    try:
        service.resume(match_id)
        return {"paused": False}
    except (MatchNotFoundError, MatchFinishedError) as exc:
        raise _http_error(exc) from exc


@router.post("/matches/{match_id}/tactics")
async def change_match_tactics(
    match_id: str, body: ChangeTacticRequest, service: MatchService = Depends(get_match_service)
) -> dict:
    try:
        service.change_tactic(match_id, body.team_id, _tactic_from_schema(body.tactic))
        return {"ok": True}
    except (MatchNotFoundError, MatchFinishedError, InvalidMatchCommandError) as exc:
        raise _http_error(exc) from exc


@router.post("/matches/{match_id}/formation")
async def change_match_formation(
    match_id: str, body: ChangeFormationRequest, service: MatchService = Depends(get_match_service)
) -> dict:
    try:
        service.change_formation(match_id, body.team_id, body.formation)
        return {"ok": True}
    except (MatchNotFoundError, MatchFinishedError, InvalidMatchCommandError) as exc:
        raise _http_error(exc) from exc


@router.post("/matches/{match_id}/substitutions")
async def substitute_player(
    match_id: str, body: SubstitutionRequest, service: MatchService = Depends(get_match_service)
) -> dict:
    try:
        service.substitute(match_id, body.team_id, body.player_out_id, body.player_in_id)
        return {"ok": True}
    except (MatchNotFoundError, MatchFinishedError, InvalidMatchCommandError) as exc:
        raise _http_error(exc) from exc


@router.get("/matches/{match_id}/events")
async def list_match_events(
    match_id: str, since_index: int = 0, service: MatchService = Depends(get_match_service)
) -> list[dict]:
    if not service.exists(match_id):
        raise HTTPException(status_code=404, detail="match not found")
    return service.get_events(match_id, since_index=since_index)


@router.get("/matches/{match_id}/statistics", response_model=MatchStatisticsSchema)
async def get_match_statistics(
    match_id: str, service: MatchService = Depends(get_match_service)
) -> MatchStatisticsSchema:
    try:
        return MatchStatisticsSchema.model_validate(service.get_statistics(match_id))
    except MatchNotFoundError as exc:
        raise _http_error(exc) from exc


@router.websocket("/matches/{match_id}/stream")
async def stream_match(
    websocket: WebSocket, match_id: str, service: MatchService = Depends(get_match_service_ws)
) -> None:
    if not service.exists(match_id):
        await websocket.close(code=_UNKNOWN_MATCH_CLOSE_CODE)
        return

    await websocket.accept()
    sent = 0
    try:
        while True:
            events = service.get_events(match_id, since_index=sent)
            for event in events:
                await websocket.send_json(event)
            sent += len(events)

            if service.is_finished(match_id) and not events:
                break

            await asyncio.sleep(_POLL_INTERVAL_SECONDS)
    except WebSocketDisconnect:
        pass


@router.get("/matches/{match_id}/snapshot", response_model=SnapshotResponse)
async def get_match_snapshot(
    match_id: str, service: MatchService = Depends(get_match_service)
) -> SnapshotResponse:
    try:
        return SnapshotResponse(snapshot=service.export_match_snapshot(match_id))
    except (MatchNotFoundError, MatchFinishedError) as exc:
        raise _http_error(exc) from exc


@router.post("/matches/{match_id}/snapshot", response_model=SnapshotResponse)
async def save_match_snapshot(
    match_id: str, service: MatchService = Depends(get_match_service)
) -> SnapshotResponse:
    try:
        return SnapshotResponse(snapshot=service.export_match_snapshot(match_id))
    except (MatchNotFoundError, MatchFinishedError) as exc:
        raise _http_error(exc) from exc


@router.post("/matches/{match_id}/restore")
async def restore_match_snapshot(
    match_id: str,
    body: RestoreSnapshotRequest,
    service: MatchService = Depends(get_match_service),
) -> dict:
    try:
        service.restore_match_snapshot(match_id, body.snapshot)
        return {"ok": True}
    except (MatchNotFoundError, MatchFinishedError, InvalidMatchCommandError, ValueError) as exc:
        raise _http_error(exc) from exc


@router.post("/matches/replay", response_model=ReplayMatchResponse)
async def replay_match_headless(
    body: ReplayMatchRequest, service: MatchService = Depends(get_match_service)
) -> ReplayMatchResponse:
    try:
        result = service.replay_match(body)
        return ReplayMatchResponse.model_validate(result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/matches/{match_id}/replay", response_model=VerifyReplayResponse)
async def verify_match_replay(
    match_id: str,
    body: ReplayMatchRequest,
    service: MatchService = Depends(get_match_service),
) -> VerifyReplayResponse:
    try:
        result = await service.verify_replay(match_id, body)
        return VerifyReplayResponse.model_validate(result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/matches/{match_id}/result", response_model=MatchResultSchema)
async def get_match_result(
    match_id: str, service: MatchService = Depends(get_match_service)
) -> MatchResultSchema:
    result = await service.get_result(match_id)
    if result is None:
        raise HTTPException(status_code=404, detail="no finished result for this match id")
    return MatchResultSchema.model_validate(result, from_attributes=True)