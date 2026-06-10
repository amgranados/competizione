"""Tournament lifecycle service (US1).

Covers tournament creation, listing, open-registration, invitations, accept/
reject/cancel, participant removal, start (with calendar generation), and the
authorization/state-guard logic.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invitation import Invitation
from app.models.match import Match
from app.models.participant import Participant
from app.models.tournament import Tournament
from app.models.user import User
from app.schemas.tournament import TournamentCreate, TournamentFormat, TournamentUpdate
from app.services import activity_service, calendar_service, notification_service

INVITATION_TTL = timedelta(hours=48)


class TournamentNotFound(Exception):
    pass


class Forbidden(Exception):
    pass


class InvalidState(Exception):
    def __init__(self, message: str = ""):
        super().__init__(message)
        self.message = message


class InvitationNotFound(Exception):
    pass


class InvitationConflict(Exception):
    pass


class InvitationExpired(Exception):
    pass


class ParticipantNotFound(Exception):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ------------------------------- queries -------------------------------


async def get_for_user(session: AsyncSession, tournament_id: uuid.UUID, user_id: uuid.UUID) -> Tournament:
    tournament = await session.get(Tournament, tournament_id)
    if tournament is None:
        raise TournamentNotFound()
    if not await _user_can_see(session, tournament, user_id):
        raise TournamentNotFound()
    return tournament


async def _user_can_see(session: AsyncSession, tournament: Tournament, user_id: uuid.UUID) -> bool:
    if tournament.organizer_id == user_id:
        return True
    p = await session.execute(
        select(Participant).where(
            Participant.tournament_id == tournament.id,
            Participant.user_id == user_id,
            Participant.removed.is_(False),
        )
    )
    if p.scalar_one_or_none() is not None:
        return True
    i = await session.execute(
        select(Invitation).where(
            Invitation.tournament_id == tournament.id,
            Invitation.invited_user_id == user_id,
            Invitation.state == "pending",
        )
    )
    return i.scalar_one_or_none() is not None


async def list_for_user(
    session: AsyncSession, user_id: uuid.UUID, state: str | None = None
) -> Sequence[Tournament]:
    # organizer OR participant (active)
    organizer_q = select(Tournament.id).where(Tournament.organizer_id == user_id)
    participant_q = select(Participant.tournament_id).where(
        Participant.user_id == user_id, Participant.removed.is_(False)
    )
    stmt = select(Tournament).where(
        or_(Tournament.id.in_(organizer_q), Tournament.id.in_(participant_q))
    )
    if state:
        stmt = stmt.where(Tournament.state == state)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def _active_participants(session: AsyncSession, tournament_id: uuid.UUID) -> list[Participant]:
    result = await session.execute(
        select(Participant).where(
            Participant.tournament_id == tournament_id,
            Participant.removed.is_(False),
        )
    )
    return list(result.scalars().all())


# ------------------------------- mutations -------------------------------


async def create(
    session: AsyncSession, *, organizer_id: uuid.UUID, payload: TournamentCreate
) -> Tournament:
    tournament = Tournament(
        name=payload.name.strip(),
        start_at=payload.start_at,
        format=payload.format.value if isinstance(payload.format, TournamentFormat) else payload.format,
        state="draft",
        organizer_id=organizer_id,
    )
    session.add(tournament)
    await session.flush()
    # 005-US3: record TOURNAMENT_CREATE for the organizer.
    await activity_service.record(
        session,
        actor_id=organizer_id,
        event_type="TOURNAMENT_CREATE",
        tournament_id=tournament.id,
    )
    return tournament


async def update(
    session: AsyncSession,
    *,
    tournament_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: TournamentUpdate,
) -> Tournament:
    tournament = await session.get(Tournament, tournament_id)
    if tournament is None:
        raise TournamentNotFound()
    if tournament.organizer_id != user_id:
        raise Forbidden()
    if tournament.state not in ("draft", "open"):
        raise InvalidState("tournament can only be modified while draft or open")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        tournament.name = data["name"].strip()
    if "start_at" in data:
        tournament.start_at = data["start_at"]
    if "format" in data and data["format"] is not None:
        tournament.format = (
            data["format"].value if isinstance(data["format"], TournamentFormat) else data["format"]
        )
    await session.flush()
    return tournament


async def open_registration(
    session: AsyncSession, *, tournament_id: uuid.UUID, user_id: uuid.UUID
) -> Tournament:
    tournament = await session.get(Tournament, tournament_id)
    if tournament is None:
        raise TournamentNotFound()
    if tournament.organizer_id != user_id:
        raise Forbidden()
    if tournament.state != "draft":
        raise InvalidState("only draft tournaments can be opened")
    tournament.state = "open"
    await session.flush()
    return tournament


async def invite(
    session: AsyncSession,
    *,
    tournament_id: uuid.UUID,
    inviter_id: uuid.UUID,
    invited_user_id: uuid.UUID,
) -> Invitation:
    tournament = await session.get(Tournament, tournament_id)
    if tournament is None:
        raise TournamentNotFound()
    if tournament.organizer_id != inviter_id:
        raise Forbidden()
    if tournament.state not in ("draft", "open"):
        raise InvalidState("can only invite while draft or open")

    # Ensure invitee exists
    invitee = await session.get(User, invited_user_id)
    if invitee is None or invitee.deleted_at is not None:
        raise InvitationConflict()

    # 004-add-friends: only friends with linked LoL account can be invited.
    from sqlalchemy import and_, or_

    from app.models.friendship import Friendship
    from app.models.riot_account import RiotAccount

    friendship_stmt = select(Friendship.id).where(
        Friendship.status == "accepted",
        or_(
            and_(
                Friendship.requester_id == inviter_id,
                Friendship.addressee_id == invited_user_id,
            ),
            and_(
                Friendship.requester_id == invited_user_id,
                Friendship.addressee_id == inviter_id,
            ),
        ),
    ).limit(1)
    if (await session.execute(friendship_stmt)).first() is None:
        raise InvitationConflict()

    riot_stmt = select(RiotAccount.id).where(
        RiotAccount.user_id == invited_user_id
    ).limit(1)
    if (await session.execute(riot_stmt)).first() is None:
        raise InvitationConflict()

    # Already participant?
    participant = await session.execute(
        select(Participant).where(
            Participant.tournament_id == tournament_id,
            Participant.user_id == invited_user_id,
            Participant.removed.is_(False),
        )
    )
    if participant.scalar_one_or_none() is not None:
        raise InvitationConflict()

    # Existing pending invitation?
    existing = await session.execute(
        select(Invitation).where(
            Invitation.tournament_id == tournament_id,
            Invitation.invited_user_id == invited_user_id,
            Invitation.state == "pending",
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise InvitationConflict()

    now = _now()
    inv = Invitation(
        tournament_id=tournament_id,
        invited_user_id=invited_user_id,
        inviter_user_id=inviter_id,
        state="pending",
        created_at=now,
        expires_at=now + INVITATION_TTL,
    )
    session.add(inv)
    await session.flush()

    await notification_service.create_notification(
        session,
        user_id=invited_user_id,
        type="invitation_received",
        tournament_id=tournament_id,
        invitation_id=inv.id,
    )
    # 005-US3: record TOURNAMENT_INVITE for the inviter (actor).
    await activity_service.record(
        session,
        actor_id=inviter_id,
        event_type="TOURNAMENT_INVITE",
        tournament_id=tournament_id,
    )
    await session.flush()
    return inv


async def cancel_invitation(
    session: AsyncSession,
    *,
    tournament_id: uuid.UUID,
    invitation_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Invitation:
    inv = await session.get(Invitation, invitation_id)
    if inv is None or inv.tournament_id != tournament_id:
        raise InvitationNotFound()
    tournament = await session.get(Tournament, tournament_id)
    if tournament is None or tournament.organizer_id != user_id:
        raise Forbidden()
    if inv.state != "pending":
        raise InvalidState("invitation is not pending")
    inv.state = "cancelled"
    inv.responded_at = _now()
    await session.flush()

    await notification_service.create_notification(
        session,
        user_id=inv.invited_user_id,
        type="invitation_cancelled",
        tournament_id=tournament_id,
        invitation_id=inv.id,
    )
    await session.flush()
    return inv


def _as_utc(dt: datetime) -> datetime:
    """Coerce naive datetimes (loaded from SQLite) to UTC-aware for comparison."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


async def _resolve_expired(session: AsyncSession, inv: Invitation) -> bool:
    """Materialize expiration when reading. Returns True if state changed."""
    if inv.state == "pending" and _as_utc(inv.expires_at) <= _now():
        inv.state = "expired"
        inv.responded_at = _now()
        await session.flush()
        return True
    return False


async def accept_invitation(
    session: AsyncSession, *, invitation_id: uuid.UUID, user_id: uuid.UUID
) -> Invitation:
    inv = await session.get(Invitation, invitation_id)
    if inv is None or inv.invited_user_id != user_id:
        raise InvitationNotFound()
    if await _resolve_expired(session, inv):
        raise InvitationExpired()
    if inv.state != "pending":
        raise InvalidState("invitation is not pending")
    tournament = await session.get(Tournament, inv.tournament_id)
    if tournament is None or tournament.state not in ("draft", "open"):
        raise InvalidState("tournament not accepting invitations")

    inv.state = "accepted"
    inv.responded_at = _now()

    # Create Participant (dedupe if it somehow exists)
    existing = await session.execute(
        select(Participant).where(
            Participant.tournament_id == inv.tournament_id,
            Participant.user_id == user_id,
        )
    )
    p = existing.scalar_one_or_none()
    if p is None:
        p = Participant(
            tournament_id=inv.tournament_id,
            user_id=user_id,
            accepted_at=_now(),
            removed=False,
        )
        session.add(p)
    else:
        p.removed = False
    await session.flush()

    await notification_service.create_notification(
        session,
        user_id=tournament.organizer_id,
        type="invitation_accepted",
        tournament_id=tournament.id,
        invitation_id=inv.id,
    )
    # 005-US3: record TOURNAMENT_JOIN for the user who joined (actor).
    await activity_service.record(
        session,
        actor_id=user_id,
        event_type="TOURNAMENT_JOIN",
        tournament_id=tournament.id,
    )
    await session.flush()
    return inv


async def reject_invitation(
    session: AsyncSession, *, invitation_id: uuid.UUID, user_id: uuid.UUID
) -> Invitation:
    inv = await session.get(Invitation, invitation_id)
    if inv is None or inv.invited_user_id != user_id:
        raise InvitationNotFound()
    if await _resolve_expired(session, inv):
        raise InvitationExpired()
    if inv.state != "pending":
        raise InvalidState("invitation is not pending")
    inv.state = "rejected"
    inv.responded_at = _now()
    await session.flush()

    tournament = await session.get(Tournament, inv.tournament_id)
    if tournament is not None:
        await notification_service.create_notification(
            session,
            user_id=tournament.organizer_id,
            type="invitation_rejected",
            tournament_id=tournament.id,
            invitation_id=inv.id,
        )
        await session.flush()
    return inv


async def list_invitations_for_tournament(
    session: AsyncSession, *, tournament_id: uuid.UUID, user_id: uuid.UUID
) -> Sequence[Invitation]:
    tournament = await session.get(Tournament, tournament_id)
    if tournament is None:
        raise TournamentNotFound()
    if tournament.organizer_id != user_id:
        raise Forbidden()
    result = await session.execute(
        select(Invitation).where(Invitation.tournament_id == tournament_id)
    )
    invitations = list(result.scalars().all())
    for inv in invitations:
        await _resolve_expired(session, inv)
    return invitations


async def list_invitations_for_user(
    session: AsyncSession, *, user_id: uuid.UUID, state: str | None = None
) -> Sequence[Invitation]:
    stmt = select(Invitation).where(Invitation.invited_user_id == user_id)
    if state:
        stmt = stmt.where(Invitation.state == state)
    result = await session.execute(stmt)
    invitations = list(result.scalars().all())
    for inv in invitations:
        await _resolve_expired(session, inv)
    return invitations


async def remove_participant(
    session: AsyncSession,
    *,
    tournament_id: uuid.UUID,
    participant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    tournament = await session.get(Tournament, tournament_id)
    if tournament is None:
        raise TournamentNotFound()
    if tournament.organizer_id != user_id:
        raise Forbidden()
    if tournament.state not in ("draft", "open"):
        raise InvalidState("cannot remove participants once the tournament has started")
    participant = await session.get(Participant, participant_id)
    if participant is None or participant.tournament_id != tournament_id:
        raise ParticipantNotFound()
    participant.removed = True
    await session.flush()


async def cancel(
    session: AsyncSession, *, tournament_id: uuid.UUID, user_id: uuid.UUID
) -> Tournament:
    tournament = await session.get(Tournament, tournament_id)
    if tournament is None:
        raise TournamentNotFound()
    if tournament.organizer_id != user_id:
        raise Forbidden()
    if tournament.state in ("finished", "cancelled"):
        raise InvalidState("tournament is in a terminal state")
    tournament.state = "cancelled"
    tournament.cancelled_at = _now()
    await session.flush()

    participants = await _active_participants(session, tournament_id)
    await notification_service.create_notifications_bulk(
        session,
        [
            {
                "user_id": p.user_id,
                "type": "tournament_cancelled",
                "tournament_id": tournament_id,
            }
            for p in participants
        ],
    )
    return tournament


async def start_tournament(
    session: AsyncSession, *, tournament_id: uuid.UUID, user_id: uuid.UUID
) -> Tournament:
    tournament = await session.get(Tournament, tournament_id)
    if tournament is None:
        raise TournamentNotFound()
    if tournament.organizer_id != user_id:
        raise Forbidden()
    if tournament.state != "open":
        raise InvalidState("tournament must be in state 'open' to start")

    participants = await _active_participants(session, tournament_id)
    if len(participants) < 2:
        raise InvalidState("need at least 2 confirmed participants to start")

    # Generate calendar using the participants (sorted by service).
    if tournament.format == "round_robin":
        rounds = calendar_service.generate_round_robin(participants)
    else:
        rounds = [calendar_service.generate_single_elim_first_round(participants)]

    for r in rounds:
        for m in r.matches:
            match = Match(
                tournament_id=tournament_id,
                round_number=m.round_number,
                bracket_position=m.bracket_position,
                player1_id=m.player1_id,
                player2_id=m.player2_id,
                is_bye=m.is_bye,
                tournament_code=m.tournament_code,
                code_created_at=m.code_created_at,
                state="pending",
            )
            session.add(match)

    tournament.state = "active"
    tournament.started_at = _now()
    await session.flush()

    # I-05: acumular todas las notificaciones de arranque y volcarlas en bloque.
    notifications: list[dict] = [
        {
            "user_id": p.user_id,
            "type": "tournament_started",
            "tournament_id": tournament_id,
        }
        for p in participants
    ]

    # match_generated for each non-bye match (fetch matches fresh for ids).
    result = await session.execute(
        select(Match).where(Match.tournament_id == tournament_id, Match.is_bye.is_(False))
    )
    by_participant = {p.id: p.user_id for p in participants}
    for match in result.scalars():
        for pid in (match.player1_id, match.player2_id):
            uid = by_participant.get(pid)
            if uid is not None:
                notifications.append(
                    {
                        "user_id": uid,
                        "type": "match_generated",
                        "tournament_id": tournament_id,
                        "match_id": match.id,
                    }
                )

    await notification_service.create_notifications_bulk(session, notifications)
    return tournament
