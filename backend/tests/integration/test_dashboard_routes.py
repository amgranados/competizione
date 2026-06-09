"""Integration tests for the dashboard (005-user-dashboard).

This module covers two layers that converge on `GET /api/dashboard`:
- US2 "Mis torneos" query (`dashboard_service.get_my_tournaments`) — FR-010/SC-004.
- The HTTP endpoint itself (auth, full response, isolation, empty new user) —
  added in the integration phase (T022).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models.activity_feed import ActivityFeed
from app.models.friendship import Friendship
from app.models.match import Match
from app.models.participant import Participant
from app.models.tournament import Tournament
from app.models.user import User
from app.services import dashboard_service
from tests.helpers import register_user


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _make_user(db_session, nickname) -> User:
    u = User(email=f"{nickname}@x.com", nickname=nickname, password_hash="x")
    db_session.add(u)
    await db_session.flush()
    return u


async def _make_tournament(
    db_session, organizer, *, name, state, fmt="round_robin", start_at=None
) -> Tournament:
    t = Tournament(
        name=name,
        format=fmt,
        state=state,
        organizer_id=organizer.id,
        start_at=start_at,
    )
    db_session.add(t)
    await db_session.flush()
    return t


async def _join(db_session, tournament, user, *, removed=False) -> Participant:
    p = Participant(tournament_id=tournament.id, user_id=user.id, removed=removed)
    db_session.add(p)
    await db_session.flush()
    return p


# --- US2: my_tournaments query (FR-010, SC-004) --------------------------


@pytest.mark.asyncio
async def test_my_tournaments_includes_in_progress_and_open_with_fields(db_session):
    me = await _make_user(db_session, "me")
    other = await _make_user(db_session, "other")
    start = _now() + timedelta(days=3)

    in_prog = await _make_tournament(
        db_session, other, name="Running", state="in_progress", fmt="single_elim"
    )
    p_me = await _join(db_session, in_prog, me)
    await _join(db_session, in_prog, other)
    # Two rounds of matches -> current_round should be the max round_number (2).
    db_session.add(
        Match(tournament_id=in_prog.id, round_number=1, player1_id=p_me.id, is_bye=True, state="manual")
    )
    db_session.add(
        Match(tournament_id=in_prog.id, round_number=2, player1_id=p_me.id, is_bye=True, state="pending")
    )
    await db_session.flush()

    upcoming = await _make_tournament(
        db_session, me, name="Soon", state="open", fmt="round_robin", start_at=start
    )
    await _join(db_session, upcoming, me)

    cards = await dashboard_service.get_my_tournaments(db_session, me)
    by_name = {c.name: c for c in cards}
    assert set(by_name) == {"Running", "Soon"}

    running = by_name["Running"]
    assert running.state == "in_progress"
    assert running.format == "single_elim"
    assert running.players_count == 2
    assert running.current_round == 2

    soon = by_name["Soon"]
    assert soon.state == "open"
    assert soon.players_count == 1
    assert soon.start_at is not None


@pytest.mark.asyncio
async def test_my_tournaments_excludes_finished_cancelled_and_foreign(db_session):
    me = await _make_user(db_session, "me")
    other = await _make_user(db_session, "other")

    finished = await _make_tournament(db_session, other, name="Done", state="finished")
    await _join(db_session, finished, me)
    cancelled = await _make_tournament(db_session, other, name="Gone", state="cancelled")
    await _join(db_session, cancelled, me)
    draft = await _make_tournament(db_session, other, name="Draft", state="draft")
    await _join(db_session, draft, me)
    # in_progress but I'm not a participant -> excluded.
    foreign = await _make_tournament(db_session, other, name="Foreign", state="in_progress")
    await _join(db_session, foreign, other)
    # in_progress but I was removed -> excluded.
    removed = await _make_tournament(db_session, other, name="Removed", state="in_progress")
    await _join(db_session, removed, me, removed=True)

    cards = await dashboard_service.get_my_tournaments(db_session, me)
    assert cards == []


@pytest.mark.asyncio
async def test_my_tournaments_treats_domain_active_token_as_in_progress(db_session):
    """State-token reconciliation (research.md Decisión 2 / T030): the domain
    stores `state="active"` (tournament_service.start_tournament), but the
    dashboard surfaces it as the contract token `in_progress`, with the round."""
    me = await _make_user(db_session, "me")
    t = await _make_tournament(db_session, me, name="Live", state="active")
    p_me = await _join(db_session, t, me)
    db_session.add(
        Match(tournament_id=t.id, round_number=4, player1_id=p_me.id, is_bye=True, state="manual")
    )
    await db_session.flush()

    cards = await dashboard_service.get_my_tournaments(db_session, me)
    assert len(cards) == 1
    assert cards[0].state == "in_progress"  # normalized from "active"
    assert cards[0].current_round == 4

    # And it is counted as an active tournament in the stats card.
    from app.services import stats_service

    stats = await stats_service.get_stats(db_session, me)
    assert stats.active_tournaments == 1


# --- GET /api/dashboard endpoint (T022) ----------------------------------


@pytest.mark.asyncio
async def test_dashboard_requires_authentication(async_client):
    async_client.cookies.clear()
    response = await async_client.get("/api/dashboard")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_dashboard_new_user_returns_neutral_stats_and_empty_arrays(async_client):
    await register_user(async_client, "fresh@example.com", "freshUser")
    response = await async_client.get("/api/dashboard")
    assert response.status_code == 200, response.text
    body = response.json()

    assert "freshUser" in body["greeting"]
    assert isinstance(body["subtitle"], str) and body["subtitle"]

    stats = body["stats"]
    assert stats["active_tournaments"] == {"count": 0, "weekly_delta": None}
    assert stats["total_wins"]["wins"] == 0
    assert stats["total_wins"]["games_played"] == 0
    assert stats["total_wins"]["winrate"] is None
    assert stats["best_streak"]["best"] == 0
    assert stats["best_streak"]["tournament_id"] is None
    assert stats["friends_count"] == 0

    assert body["my_tournaments"] == []
    assert body["activity"] == []


@pytest.mark.asyncio
async def test_dashboard_returns_full_response_for_user_with_history(async_client, db_session):
    user = await register_user(async_client, "owner@example.com", "ownerUser")
    me = await db_session.get(User, uuid.UUID(user["id"]))

    # A friend whose event should appear; a stranger whose event must not.
    friend = await _make_user(db_session, "buddy")
    stranger = await _make_user(db_session, "rando")
    db_session.add(Friendship(requester_id=me.id, addressee_id=friend.id, status="accepted"))

    t = await _make_tournament(db_session, me, name="Live Cup", state="in_progress")
    await _join(db_session, t, me)
    await _join(db_session, t, friend)

    db_session.add(ActivityFeed(actor_id=me.id, event_type="TOURNAMENT_CREATE", tournament_id=t.id))
    db_session.add(ActivityFeed(actor_id=friend.id, event_type="MATCH_WIN", tournament_id=t.id))
    db_session.add(ActivityFeed(actor_id=stranger.id, event_type="MATCH_WIN", tournament_id=t.id))
    await db_session.commit()

    response = await async_client.get("/api/dashboard")
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["greeting"] == "Hola, ownerUser"
    assert body["stats"]["friends_count"] == 1

    names = {c["name"] for c in body["my_tournaments"]}
    assert "Live Cup" in names

    # Feed: own + friend events present, stranger excluded (isolation, SC-005).
    actor_nicks = {e["actor"]["nickname"] for e in body["activity"]}
    assert "ownerUser" in actor_nicks
    assert "buddy" in actor_nicks
    assert "rando" not in actor_nicks
    assert len(body["activity"]) <= 6
