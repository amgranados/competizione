from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_current_user
from app.db.base import get_db
from app.models.match import Match as MatchModel
from app.models.participant import Participant as ParticipantModel
from app.models.tournament import Tournament as TournamentModel
from app.models.user import User
from app.schemas.match import ManualResultRequest
from app.schemas.match import Match as MatchSchema
from app.services import match_service

router = APIRouter(tags=["matches"])


def _match_to_schema(match: MatchModel, *, hide_code: bool) -> MatchSchema:
    return MatchSchema(
        id=match.id,
        tournament_id=match.tournament_id,
        round_number=match.round_number,
        bracket_position=match.bracket_position,
        player1_id=match.player1_id,
        player2_id=match.player2_id,
        is_bye=match.is_bye,
        tournament_code=None if hide_code else match.tournament_code,
        code_created_at=match.code_created_at,
        state=match.state,
        winner_participant_id=match.winner_participant_id,
        resolved_at=match.resolved_at,
    )


async def _hide_code_for(session: AsyncSession, match: MatchModel, viewer: User) -> bool:
    tournament = await session.get(TournamentModel, match.tournament_id)
    if tournament is None:
        return True
    if tournament.organizer_id == viewer.id:
        return False
    for pid in (match.player1_id, match.player2_id):
        if pid is None:
            continue
        participant = await session.get(ParticipantModel, pid)
        if participant is not None and participant.user_id == viewer.id:
            return False
    return True


async def _viewer_allowed(session: AsyncSession, match: MatchModel, viewer: User) -> bool:
    tournament = await session.get(TournamentModel, match.tournament_id)
    if tournament is None:
        return False
    if tournament.organizer_id == viewer.id:
        return True
    # Any active participant can view.
    result = await session.execute(
        select(ParticipantModel).where(
            ParticipantModel.tournament_id == tournament.id,
            ParticipantModel.user_id == viewer.id,
            ParticipantModel.removed.is_(False),
        )
    )
    return result.scalar_one_or_none() is not None


@router.get("/matches/{match_id}", response_model=MatchSchema)
async def get_match(
    match_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MatchSchema:
    match = await session.get(MatchModel, match_id)
    if match is None or not await _viewer_allowed(session, match, current_user):
        raise HTTPException(status_code=404, detail="Not found")
    hide_code = await _hide_code_for(session, match, current_user)
    return _match_to_schema(match, hide_code=hide_code)


@router.get("/matches/{match_id}/lobby-events")
async def get_lobby_events(
    match_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """Eventos de la lobby del código de torneo (Tournament-Stub-V5).

    Visible para quien puede ver el código (organizador o jugadores de la
    partida). Si Riot no está disponible o la partida no tiene código, lista
    vacía: es información auxiliar, nunca bloqueante.
    """
    from app.core.config import get_settings
    from app.services.riot_api.client import (
        RiotIdentityError,
        RiotUnavailableError,
        get_riot_api_client,
    )

    match = await session.get(MatchModel, match_id)
    if match is None or not await _viewer_allowed(session, match, current_user):
        raise HTTPException(status_code=404, detail="Not found")
    if await _hide_code_for(session, match, current_user) or not match.tournament_code:
        return []
    client = get_riot_api_client(get_settings())
    try:
        events = await client.get_lobby_events(match.tournament_code)
    except (RiotIdentityError, RiotUnavailableError):
        return []
    return [
        {"timestamp": e.timestamp, "event_type": e.event_type, "puuid": e.puuid}
        for e in events
    ]


@router.post("/matches/{match_id}/manual-result", response_model=MatchSchema)
async def register_manual_result(
    match_id: uuid.UUID,
    payload: ManualResultRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MatchSchema:
    try:
        match = await match_service.register_manual_result(
            session,
            match_id=match_id,
            winner_participant_id=payload.winner_participant_id,
            acting_user_id=current_user.id,
        )
    except match_service.MatchNotFound:
        raise HTTPException(status_code=404, detail="Not found")
    except match_service.Forbidden:
        raise HTTPException(status_code=403, detail="Forbidden")
    except match_service.InvalidState as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    await session.commit()
    return _match_to_schema(match, hide_code=False)
