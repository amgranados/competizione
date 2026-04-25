from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_current_user
from app.db.base import get_db
from app.models.invitation import Invitation as InvitationModel
from app.models.match import Match as MatchModel
from app.models.participant import Participant as ParticipantModel
from app.models.tournament import Tournament as TournamentModel
from app.models.user import User
from app.schemas.tournament import (
    Invitation as InvitationSchema,
    InvitationCreate,
    RoundMatchSummary,
    RoundView,
    Schedule,
    StandingEntry,
    Tournament as TournamentSchema,
    TournamentCreate,
    TournamentFormat,
    TournamentState,
    TournamentUpdate,
)
from app.services import standings_service, tournament_service

router = APIRouter(tags=["tournaments"])


def _forbidden():
    return HTTPException(status_code=403, detail="Forbidden")


def _conflict(msg: str = "Conflict"):
    return HTTPException(status_code=409, detail=msg)


def _not_found():
    return HTTPException(status_code=404, detail="Not found")


async def _tournament_to_schema(
    session: AsyncSession, tournament: TournamentModel
) -> TournamentSchema:
    # participants with nickname
    stmt = (
        select(ParticipantModel, User.nickname)
        .join(User, User.id == ParticipantModel.user_id)
        .where(
            ParticipantModel.tournament_id == tournament.id,
            ParticipantModel.removed.is_(False),
        )
    )
    result = await session.execute(stmt)
    participants = []
    for participant, nickname in result.all():
        participants.append(
            {
                "id": participant.id,
                "user_id": participant.user_id,
                "nickname": nickname,
                "accepted_at": participant.accepted_at,
            }
        )
    return TournamentSchema(
        id=tournament.id,
        name=tournament.name,
        start_at=tournament.start_at,
        format=tournament.format,
        state=tournament.state,
        organizer_id=tournament.organizer_id,
        created_at=tournament.created_at,
        started_at=tournament.started_at,
        finished_at=tournament.finished_at,
        cancelled_at=tournament.cancelled_at,
        participants=participants,
    )


# ------------------------------- tournaments -------------------------------


@router.post("/tournaments", status_code=201, response_model=TournamentSchema)
async def create_tournament(
    payload: TournamentCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TournamentSchema:
    tournament = await tournament_service.create(
        session, organizer_id=current_user.id, payload=payload
    )
    await session.commit()
    return await _tournament_to_schema(session, tournament)


@router.get("/tournaments", response_model=list[TournamentSchema])
async def list_tournaments(
    state: TournamentState | None = None,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TournamentSchema]:
    tournaments = await tournament_service.list_for_user(
        session, current_user.id, state=state.value if state else None
    )
    return [await _tournament_to_schema(session, t) for t in tournaments]


@router.get("/tournaments/{tournament_id}", response_model=TournamentSchema)
async def get_tournament(
    tournament_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TournamentSchema:
    try:
        tournament = await tournament_service.get_for_user(session, tournament_id, current_user.id)
    except tournament_service.TournamentNotFound:
        raise _not_found()
    return await _tournament_to_schema(session, tournament)


@router.patch("/tournaments/{tournament_id}", response_model=TournamentSchema)
async def update_tournament(
    tournament_id: uuid.UUID,
    payload: TournamentUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TournamentSchema:
    try:
        tournament = await tournament_service.update(
            session, tournament_id=tournament_id, user_id=current_user.id, payload=payload
        )
    except tournament_service.TournamentNotFound:
        raise _not_found()
    except tournament_service.Forbidden:
        raise _forbidden()
    except tournament_service.InvalidState as exc:
        raise _conflict(str(exc))
    await session.commit()
    return await _tournament_to_schema(session, tournament)


@router.post("/tournaments/{tournament_id}/open", response_model=TournamentSchema)
async def open_registration(
    tournament_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TournamentSchema:
    try:
        tournament = await tournament_service.open_registration(
            session, tournament_id=tournament_id, user_id=current_user.id
        )
    except tournament_service.TournamentNotFound:
        raise _not_found()
    except tournament_service.Forbidden:
        raise _forbidden()
    except tournament_service.InvalidState as exc:
        raise _conflict(str(exc))
    await session.commit()
    return await _tournament_to_schema(session, tournament)


@router.post("/tournaments/{tournament_id}/cancel", response_model=TournamentSchema)
async def cancel_tournament(
    tournament_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TournamentSchema:
    try:
        tournament = await tournament_service.cancel(
            session, tournament_id=tournament_id, user_id=current_user.id
        )
    except tournament_service.TournamentNotFound:
        raise _not_found()
    except tournament_service.Forbidden:
        raise _forbidden()
    except tournament_service.InvalidState as exc:
        raise _conflict(str(exc))
    await session.commit()
    return await _tournament_to_schema(session, tournament)


@router.post("/tournaments/{tournament_id}/start", response_model=TournamentSchema)
async def start_tournament(
    tournament_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TournamentSchema:
    try:
        tournament = await tournament_service.start_tournament(
            session, tournament_id=tournament_id, user_id=current_user.id
        )
    except tournament_service.TournamentNotFound:
        raise _not_found()
    except tournament_service.Forbidden:
        raise _forbidden()
    except tournament_service.InvalidState as exc:
        raise _conflict(str(exc))
    await session.commit()
    return await _tournament_to_schema(session, tournament)


# -------------------------------- invitations --------------------------------


def _invitation_to_schema(inv: InvitationModel) -> InvitationSchema:
    return InvitationSchema.model_validate(inv)


@router.post(
    "/tournaments/{tournament_id}/invitations",
    status_code=201,
    response_model=InvitationSchema,
)
async def invite(
    tournament_id: uuid.UUID,
    payload: InvitationCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvitationSchema:
    try:
        inv = await tournament_service.invite(
            session,
            tournament_id=tournament_id,
            inviter_id=current_user.id,
            invited_user_id=payload.invited_user_id,
        )
    except tournament_service.TournamentNotFound:
        raise _not_found()
    except tournament_service.Forbidden:
        raise _forbidden()
    except tournament_service.InvitationConflict:
        raise _conflict("user cannot be invited")
    except tournament_service.InvalidState as exc:
        raise _conflict(str(exc))
    await session.commit()
    await session.refresh(inv)
    return _invitation_to_schema(inv)


@router.get("/tournaments/{tournament_id}/invitations", response_model=list[InvitationSchema])
async def list_tournament_invitations(
    tournament_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InvitationSchema]:
    try:
        invitations = await tournament_service.list_invitations_for_tournament(
            session, tournament_id=tournament_id, user_id=current_user.id
        )
    except tournament_service.TournamentNotFound:
        raise _not_found()
    except tournament_service.Forbidden:
        raise _forbidden()
    await session.commit()
    return [_invitation_to_schema(i) for i in invitations]


@router.post(
    "/tournaments/{tournament_id}/invitations/{invitation_id}/cancel",
    response_model=InvitationSchema,
)
async def cancel_invitation(
    tournament_id: uuid.UUID,
    invitation_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvitationSchema:
    try:
        inv = await tournament_service.cancel_invitation(
            session,
            tournament_id=tournament_id,
            invitation_id=invitation_id,
            user_id=current_user.id,
        )
    except tournament_service.InvitationNotFound:
        raise _not_found()
    except tournament_service.Forbidden:
        raise _forbidden()
    except tournament_service.InvalidState as exc:
        raise _conflict(str(exc))
    await session.commit()
    return _invitation_to_schema(inv)


@router.get("/invitations", response_model=list[InvitationSchema])
async def list_my_invitations(
    state: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InvitationSchema]:
    invitations = await tournament_service.list_invitations_for_user(
        session, user_id=current_user.id, state=state
    )
    await session.commit()
    return [_invitation_to_schema(i) for i in invitations]


@router.post("/invitations/{invitation_id}/accept", response_model=InvitationSchema)
async def accept_invitation(
    invitation_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvitationSchema:
    try:
        inv = await tournament_service.accept_invitation(
            session, invitation_id=invitation_id, user_id=current_user.id
        )
    except tournament_service.InvitationNotFound:
        raise _not_found()
    except tournament_service.InvitationExpired:
        raise HTTPException(status_code=410, detail="invitation expired")
    except tournament_service.InvalidState as exc:
        raise _conflict(str(exc))
    await session.commit()
    return _invitation_to_schema(inv)


@router.post("/invitations/{invitation_id}/reject", response_model=InvitationSchema)
async def reject_invitation(
    invitation_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvitationSchema:
    try:
        inv = await tournament_service.reject_invitation(
            session, invitation_id=invitation_id, user_id=current_user.id
        )
    except tournament_service.InvitationNotFound:
        raise _not_found()
    except tournament_service.InvitationExpired:
        raise HTTPException(status_code=410, detail="invitation expired")
    except tournament_service.InvalidState as exc:
        raise _conflict(str(exc))
    await session.commit()
    return _invitation_to_schema(inv)


# -------------------------------- participants --------------------------------


@router.delete(
    "/tournaments/{tournament_id}/participants/{participant_id}", status_code=204
)
async def remove_participant(
    tournament_id: uuid.UUID,
    participant_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await tournament_service.remove_participant(
            session,
            tournament_id=tournament_id,
            participant_id=participant_id,
            user_id=current_user.id,
        )
    except tournament_service.TournamentNotFound:
        raise _not_found()
    except tournament_service.ParticipantNotFound:
        raise _not_found()
    except tournament_service.Forbidden:
        raise _forbidden()
    except tournament_service.InvalidState as exc:
        raise _conflict(str(exc))
    await session.commit()
    return None


# -------------------------------- schedule --------------------------------


async def _build_schedule(
    session: AsyncSession, tournament: TournamentModel, viewer: User
) -> Schedule:
    # Active participants for the viewer / code visibility rule.
    stmt = select(ParticipantModel).where(
        ParticipantModel.tournament_id == tournament.id
    )
    parts = list((await session.execute(stmt)).scalars().all())
    part_by_id = {p.id: p for p in parts}

    matches_stmt = (
        select(MatchModel)
        .where(MatchModel.tournament_id == tournament.id)
        .order_by(MatchModel.round_number, MatchModel.bracket_position)
    )
    matches = list((await session.execute(matches_stmt)).scalars().all())

    rounds_by_number: dict[int, list[MatchModel]] = {}
    for m in matches:
        rounds_by_number.setdefault(m.round_number, []).append(m)

    rounds_view: list[RoundView] = []
    for number in sorted(rounds_by_number):
        match_summaries = []
        for m in rounds_by_number[number]:
            # Visibility of tournament_code: organizer or either player.
            viewer_can_see_code = tournament.organizer_id == viewer.id
            if not viewer_can_see_code:
                for pid in (m.player1_id, m.player2_id):
                    p = part_by_id.get(pid) if pid else None
                    if p is not None and p.user_id == viewer.id:
                        viewer_can_see_code = True
                        break
            code = m.tournament_code if viewer_can_see_code else None
            match_summaries.append(
                RoundMatchSummary(
                    id=m.id,
                    round_number=m.round_number,
                    bracket_position=m.bracket_position,
                    player1_id=m.player1_id,
                    player2_id=m.player2_id,
                    is_bye=m.is_bye,
                    tournament_code=code,
                    state=m.state,
                    winner_participant_id=m.winner_participant_id,
                )
            )
        rounds_view.append(RoundView(number=number, matches=match_summaries))

    return Schedule(format=TournamentFormat(tournament.format), rounds=rounds_view)


@router.get("/tournaments/{tournament_id}/schedule", response_model=Schedule)
async def get_schedule(
    tournament_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Schedule:
    try:
        tournament = await tournament_service.get_for_user(session, tournament_id, current_user.id)
    except tournament_service.TournamentNotFound:
        raise _not_found()
    return await _build_schedule(session, tournament, current_user)


@router.get("/tournaments/{tournament_id}/standings", response_model=list[StandingEntry])
async def get_standings(
    tournament_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[StandingEntry]:
    try:
        tournament = await tournament_service.get_for_user(session, tournament_id, current_user.id)
    except tournament_service.TournamentNotFound:
        raise _not_found()
    if tournament.format != "round_robin":
        raise _not_found()
    return await standings_service.compute(session, tournament)


@router.get("/tournaments/{tournament_id}/bracket", response_model=Schedule)
async def get_bracket(
    tournament_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Schedule:
    try:
        tournament = await tournament_service.get_for_user(session, tournament_id, current_user.id)
    except tournament_service.TournamentNotFound:
        raise _not_found()
    if tournament.format != "single_elim":
        raise _not_found()
    return await _build_schedule(session, tournament, current_user)
