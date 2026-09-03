"""Unit tests for activity_service (005-user-dashboard, US3).

`record(...)` writes one event; `list_recent(...)` reads the ≤6 most recent
events visible to the user (own + accepted friends), newest first, resilient to
deleted users/tournaments.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.activity_feed import ActivityFeed
from app.models.friendship import Friendship
from app.models.tournament import Tournament
from app.models.user import User
from app.services import activity_service


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _make_user(db_session, nickname, *, deleted=False) -> User:
    u = User(email=f"{nickname}@x.com", nickname=nickname, password_hash="x")
    if deleted:
        u.deleted_at = _now()
    db_session.add(u)
    await db_session.flush()
    return u


async def _befriend(db_session, a, b) -> Friendship:
    f = Friendship(requester_id=a.id, addressee_id=b.id, status="accepted")
    db_session.add(f)
    await db_session.flush()
    return f


async def _make_tournament(db_session, organizer, name="T") -> Tournament:
    t = Tournament(name=name, format="round_robin", state="open", organizer_id=organizer.id)
    db_session.add(t)
    await db_session.flush()
    return t


async def _seed_event(db_session, actor, event_type, *, tournament=None, created_at=None):
    ev = ActivityFeed(
        actor_id=actor.id,
        event_type=event_type,
        tournament_id=tournament.id if tournament is not None else None,
        created_at=created_at or _now(),
    )
    db_session.add(ev)
    await db_session.flush()
    return ev


# --- record(...) ----------------------------------------------------------


@pytest.mark.asyncio
async def test_record_inserts_a_row(db_session):
    me = await _make_user(db_session, "me")
    t = await _make_tournament(db_session, me)
    await activity_service.record(
        db_session, actor_id=me.id, event_type="TOURNAMENT_CREATE", tournament_id=t.id
    )
    rows = (await db_session.execute(select(ActivityFeed))).scalars().all()
    assert len(rows) == 1
    assert rows[0].actor_id == me.id
    assert rows[0].event_type == "TOURNAMENT_CREATE"
    assert rows[0].tournament_id == t.id
    assert rows[0].created_at is not None


# --- list_recent visibility + ordering ------------------------------------


@pytest.mark.asyncio
async def test_list_recent_includes_own_events(db_session):
    me = await _make_user(db_session, "me")
    t = await _make_tournament(db_session, me)
    await _seed_event(db_session, me, "TOURNAMENT_CREATE", tournament=t)

    entries = await activity_service.list_recent(db_session, me)
    assert len(entries) == 1
    assert entries[0].actor_id == me.id
    assert entries[0].event_type == "TOURNAMENT_CREATE"


@pytest.mark.asyncio
async def test_list_recent_includes_friends_excludes_strangers(db_session):
    me = await _make_user(db_session, "me")
    friend = await _make_user(db_session, "friend")
    stranger = await _make_user(db_session, "stranger")
    await _befriend(db_session, me, friend)

    await _seed_event(db_session, friend, "MATCH_WIN")
    await _seed_event(db_session, stranger, "MATCH_WIN")

    entries = await activity_service.list_recent(db_session, me)
    actor_ids = {e.actor_id for e in entries}
    assert friend.id in actor_ids
    assert stranger.id not in actor_ids


@pytest.mark.asyncio
async def test_list_recent_limited_to_six(db_session):
    me = await _make_user(db_session, "me")
    base = _now()
    for i in range(8):
        await _seed_event(
            db_session, me, "MATCH_WIN", created_at=base + timedelta(minutes=i)
        )
    entries = await activity_service.list_recent(db_session, me)
    assert len(entries) == 6


@pytest.mark.asyncio
async def test_list_recent_newest_first(db_session):
    me = await _make_user(db_session, "me")
    base = _now()
    old = await _seed_event(db_session, me, "MATCH_WIN", created_at=base)
    mid = await _seed_event(db_session, me, "TOURNAMENT_JOIN", created_at=base + timedelta(minutes=5))
    new = await _seed_event(db_session, me, "TOURNAMENT_CREATE", created_at=base + timedelta(minutes=10))

    entries = await activity_service.list_recent(db_session, me)
    assert [e.id for e in entries] == [new.id, mid.id, old.id]


@pytest.mark.asyncio
async def test_list_recent_excludes_anonymized_friend_events(db_session):
    me = await _make_user(db_session, "me")
    friend = await _make_user(db_session, "friend")
    await _befriend(db_session, me, friend)
    await _seed_event(db_session, friend, "MATCH_WIN")
    # Friend gets anonymized after the event.
    friend.deleted_at = _now()
    await db_session.flush()

    entries = await activity_service.list_recent(db_session, me)
    assert all(e.actor_id != friend.id for e in entries)


@pytest.mark.asyncio
async def test_list_recent_resilient_to_deleted_tournament(db_session):
    me = await _make_user(db_session, "me")
    # tournament_id NULL emulates a deleted tournament (ON DELETE SET NULL).
    await _seed_event(db_session, me, "TOURNAMENT_JOIN", tournament=None)

    entries = await activity_service.list_recent(db_session, me)
    assert len(entries) == 1
    # Resilient entry: no tournament link, no crash (FR-022).
    assert entries[0].tournament_id is None
    assert entries[0].tournament_name is None


@pytest.mark.asyncio
async def test_list_recent_resolves_actor_and_tournament_fields(db_session):
    me = await _make_user(db_session, "me")
    t = await _make_tournament(db_session, me, name="Spring Cup")
    await _seed_event(db_session, me, "TOURNAMENT_CREATE", tournament=t)

    entries = await activity_service.list_recent(db_session, me)
    e = entries[0]
    assert e.actor_nickname == "me"
    assert e.actor_exists is True
    assert e.tournament_id == t.id
    assert e.tournament_name == "Spring Cup"
