"""Unit tests for tournament_service activity instrumentation
(005-user-dashboard, US3).

Verifies the additive activity events emitted at the action (research.md
Decisión 3): TOURNAMENT_CREATE (new Tournament), TOURNAMENT_INVITE (new
Invitation), TOURNAMENT_JOIN (new Participant via accepted invitation). These
do not change any existing tournament_service contract.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.activity_feed import ActivityFeed
from app.models.friendship import Friendship
from app.models.riot_account import RiotAccount
from app.models.user import User
from app.schemas.tournament import TournamentCreate, TournamentFormat
from app.services import tournament_service


async def _make_user(db_session, nickname) -> User:
    u = User(email=f"{nickname}@x.com", nickname=nickname, password_hash="x")
    db_session.add(u)
    await db_session.flush()
    return u


async def _link_riot(db_session, user) -> RiotAccount:
    acc = RiotAccount(
        user_id=user.id,
        puuid=f"puuid-{user.nickname}",
        game_name=user.nickname,
        tag_line="EUW",
        region="EUW1",
    )
    db_session.add(acc)
    await db_session.flush()
    return acc


async def _befriend(db_session, a, b) -> Friendship:
    f = Friendship(requester_id=a.id, addressee_id=b.id, status="accepted")
    db_session.add(f)
    await db_session.flush()
    return f


async def _events(db_session, event_type):
    return (
        await db_session.execute(
            select(ActivityFeed).where(ActivityFeed.event_type == event_type)
        )
    ).scalars().all()


# --- TOURNAMENT_CREATE ----------------------------------------------------


@pytest.mark.asyncio
async def test_create_records_tournament_create_event(db_session):
    organizer = await _make_user(db_session, "org")
    tournament = await tournament_service.create(
        db_session,
        organizer_id=organizer.id,
        payload=TournamentCreate(name="My Cup", format=TournamentFormat.ROUND_ROBIN),
    )
    events = await _events(db_session, "TOURNAMENT_CREATE")
    assert len(events) == 1
    assert events[0].actor_id == organizer.id
    assert events[0].tournament_id == tournament.id


# --- TOURNAMENT_INVITE ----------------------------------------------------


@pytest.mark.asyncio
async def test_invite_records_tournament_invite_event(db_session):
    organizer = await _make_user(db_session, "org")
    invitee = await _make_user(db_session, "guest")
    await _link_riot(db_session, invitee)
    await _befriend(db_session, organizer, invitee)

    tournament = await tournament_service.create(
        db_session,
        organizer_id=organizer.id,
        payload=TournamentCreate(name="Invite Cup", format=TournamentFormat.ROUND_ROBIN),
    )
    await tournament_service.open_registration(
        db_session, tournament_id=tournament.id, user_id=organizer.id
    )
    await tournament_service.invite(
        db_session,
        tournament_id=tournament.id,
        inviter_id=organizer.id,
        invited_user_id=invitee.id,
    )

    events = await _events(db_session, "TOURNAMENT_INVITE")
    assert len(events) == 1
    # Actor is the inviter (research.md Decisión 3).
    assert events[0].actor_id == organizer.id
    assert events[0].tournament_id == tournament.id


# --- TOURNAMENT_JOIN ------------------------------------------------------


@pytest.mark.asyncio
async def test_accept_invitation_records_tournament_join_event(db_session):
    organizer = await _make_user(db_session, "org")
    invitee = await _make_user(db_session, "guest")
    await _link_riot(db_session, invitee)
    await _befriend(db_session, organizer, invitee)

    tournament = await tournament_service.create(
        db_session,
        organizer_id=organizer.id,
        payload=TournamentCreate(name="Join Cup", format=TournamentFormat.ROUND_ROBIN),
    )
    await tournament_service.open_registration(
        db_session, tournament_id=tournament.id, user_id=organizer.id
    )
    invitation = await tournament_service.invite(
        db_session,
        tournament_id=tournament.id,
        inviter_id=organizer.id,
        invited_user_id=invitee.id,
    )
    await tournament_service.accept_invitation(
        db_session, invitation_id=invitation.id, user_id=invitee.id
    )

    events = await _events(db_session, "TOURNAMENT_JOIN")
    assert len(events) == 1
    # Actor is the user who joined.
    assert events[0].actor_id == invitee.id
    assert events[0].tournament_id == tournament.id
