"""FastAPI routes for match creation and live streaming — thin per
backend/CLAUDE.md and delivery/CLAUDE.md: parse the request, call
MatchService, shape the response. Any actual logic belongs in
delivery/services/match_service.py, not here.
"""

import asyncio

from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect

from app.delivery.schemas import CreateMatchRequest, CreateMatchResponse, context_from_request, team_from_schema
from app.delivery.services.match_service import MatchService

router = APIRouter()

_POLL_INTERVAL_SECONDS = 0.05
_UNKNOWN_MATCH_CLOSE_CODE = 4004


def get_match_service(request: Request) -> MatchService:
    return request.app.state.match_service


def get_match_service_ws(websocket: WebSocket) -> MatchService:
    return websocket.app.state.match_service


@router.post("/matches", response_model=CreateMatchResponse)
async def create_match(
    body: CreateMatchRequest, service: MatchService = Depends(get_match_service)
) -> CreateMatchResponse:
    team_a = team_from_schema(body.team_a)
    team_b = team_from_schema(body.team_b)
    context = context_from_request(body)
    match_id = await service.start_match(team_a, team_b, body.seed, context)
    return CreateMatchResponse(match_id=match_id)


@router.websocket("/matches/{match_id}/stream")
async def stream_match(
    websocket: WebSocket, match_id: str, service: MatchService = Depends(get_match_service_ws)
) -> None:
    """Sends the backlog immediately (no delay), then polls for new events
    as they're appended by the background simulation — see
    delivery/CLAUDE.md's session lifecycle. A late-joining viewer and a
    viewer who's been connected from kickoff both just read from the same
    growing event log; the engine is never re-invoked per viewer."""
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
