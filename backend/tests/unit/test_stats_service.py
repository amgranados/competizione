"""Unit tests for stats_service (005-user-dashboard, US1).

Covers the 4 stat cards computed hot from the user's own history
(research.md Decisión 5):
- active tournaments (in_progress, user participates) + weekly delta
- total wins (excl. byes) + games_played + winrate (0, no ZeroDivision)
- best streak within one tournament (last win's tournament ref)
- friends_count (accepted, both directions, excl. deleted)
- empty user → all neutral, no error
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.friendship import Friendship
from app.models.match import Match
from app.models.participant import Participant
from app.models.tournament import Tournament
from app.models.user import User
from app.services import stats_service


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _make_user(db_session, nickname, *, deleted=False) -> User:
    u = User(email=f"{nickname}@x.com", nickname=nickname, password_hash="x")
    if deleted:
        u.deleted_at = _now()
    db_session.add(u)
    await db_session.flush()
    return u


async def _make_tournament(
    db_session, organizer, *, name="T", state="in_progress", started_at=None, finished_at=None
) -> Tournament:
    t = Tournament(
        name=name,
        format="round_robin",
        state=state,
        organizer_id=organizer.id,
        started_at=started_at,
        finished_at=finished_at,
    )
    db_session.add(t)
    await db_session.flush()
    return t


async def _make_participant(db_session, tournament, user, *, removed=False) -> Participant:
    p = Participant(tournament_id=tournament.id, user_id=user.id, removed=removed)
    db_session.add(p)
    await db_session.flush()
    return p


async def _make_match(
    db_session, tournament, p1, p2, *, is_bye=False, winner=None, state="manual", resolved_at=None
) -> Match:
    m = Match(
        tournament_id=tournament.id,
        round_number=1,
        player1_id=p1.id,
        player2_id=p2.id if p2 is not None else None,
        is_bye=is_bye,
        tournament_code=None if is_bye else "tc",
        state=state,
        winner_participant_id=winner.id if winner is not None else None,
        resolved_at=resolved_at if resolved_at is not None else _now(),
    )
    db_session.add(m)
    await db_session.flush()
    return m


# --- active tournaments + weekly delta (FR-003, FR-004) ------------------


@pytest.mark.asyncio
async def test_active_tournaments_counts_only_in_progress_where_user_participates(db_session):
    me = await _make_user(db_session, "me")
    other = await _make_user(db_session, "other")
    # in_progress, I participate -> counts
    t1 = await _make_tournament(db_session, other, name="A", state="in_progress")
    await _make_participant(db_session, t1, me)
    # open, I participate -> NOT an active tournament (only in_progress counts)
    t2 = await _make_tournament(db_session, other, name="B", state="open")
    await _make_participant(db_session, t2, me)
    # in_progress, I do NOT participate -> not counted
    t3 = await _make_tournament(db_session, other, name="C", state="in_progress")
    await _make_participant(db_session, t3, other)
    # in_progress but I'm a removed participant -> not counted
    t4 = await _make_tournament(db_session, other, name="D", state="in_progress")
    await _make_participant(db_session, t4, me, removed=True)

    stats = await stats_service.get_stats(db_session, me)
    assert stats.active_tournaments == 1


@pytest.mark.asyncio
async def test_weekly_delta_is_difference_vs_seven_days_ago(db_session):
    me = await _make_user(db_session, "me")
    now = _now()
    # Active now AND active 7d ago (started 10d ago, still running) -> in both counts.
    t_old = await _make_tournament(
        db_session, me, name="Old", state="in_progress", started_at=now - timedelta(days=10)
    )
    await _make_participant(db_session, t_old, me)
    # Active now, started 2 days ago -> in "now" but NOT in "7d ago".
    t_new = await _make_tournament(
        db_session, me, name="New", state="in_progress", started_at=now - timedelta(days=2)
    )
    await _make_participant(db_session, t_new, me)

    stats = await stats_service.get_stats(db_session, me)
    assert stats.active_tournaments == 2
    # 7 days ago only t_old was running -> delta = 2 - 1 = 1
    assert stats.weekly_delta == 1


@pytest.mark.asyncio
async def test_weekly_delta_neutral_when_no_history(db_session):
    me = await _make_user(db_session, "me")
    stats = await stats_service.get_stats(db_session, me)
    assert stats.active_tournaments == 0
    # No tournaments at all -> neutral, not a misleading number.
    assert stats.weekly_delta is None


# --- wins / winrate (FR-005, FR-008) -------------------------------------


@pytest.mark.asyncio
async def test_total_wins_exclude_byes(db_session):
    me = await _make_user(db_session, "me")
    opp = await _make_user(db_session, "opp")
    t = await _make_tournament(db_session, me, state="in_progress")
    pme = await _make_participant(db_session, t, me)
    popp = await _make_participant(db_session, t, opp)
    # One real win.
    await _make_match(db_session, t, pme, popp, winner=pme)
    # One bye that I "win" -> must NOT count as a win.
    await _make_match(db_session, t, pme, None, is_bye=True, winner=pme)

    stats = await stats_service.get_stats(db_session, me)
    assert stats.total_wins == 1
    assert stats.games_played == 1  # the bye is not a played game either


@pytest.mark.asyncio
async def test_winrate_zero_without_games_no_zero_division(db_session):
    me = await _make_user(db_session, "me")
    stats = await stats_service.get_stats(db_session, me)
    assert stats.total_wins == 0
    assert stats.games_played == 0
    # No division by zero; winrate is None (no games) — neutral.
    assert stats.winrate is None


@pytest.mark.asyncio
async def test_winrate_is_wins_over_games_times_100(db_session):
    me = await _make_user(db_session, "me")
    opp = await _make_user(db_session, "opp")
    t = await _make_tournament(db_session, me, state="in_progress")
    pme = await _make_participant(db_session, t, me)
    popp = await _make_participant(db_session, t, opp)
    # 3 wins, 1 loss -> 4 games -> 75%
    for _ in range(3):
        await _make_match(db_session, t, pme, popp, winner=pme)
    await _make_match(db_session, t, pme, popp, winner=popp)

    stats = await stats_service.get_stats(db_session, me)
    assert stats.total_wins == 3
    assert stats.games_played == 4
    assert stats.winrate == pytest.approx(75.0)


# --- best streak (FR-006, Assumption) ------------------------------------


@pytest.mark.asyncio
async def test_best_streak_is_max_consecutive_wins_within_one_tournament(db_session):
    me = await _make_user(db_session, "me")
    opp = await _make_user(db_session, "opp")
    base = _now()
    # Tournament 1: W W L W -> best run here is 2.
    t1 = await _make_tournament(db_session, me, name="T1", state="finished")
    pme1 = await _make_participant(db_session, t1, me)
    popp1 = await _make_participant(db_session, t1, opp)
    await _make_match(db_session, t1, pme1, popp1, winner=pme1, resolved_at=base + timedelta(minutes=1))
    await _make_match(db_session, t1, pme1, popp1, winner=pme1, resolved_at=base + timedelta(minutes=2))
    await _make_match(db_session, t1, pme1, popp1, winner=popp1, resolved_at=base + timedelta(minutes=3))
    await _make_match(db_session, t1, pme1, popp1, winner=pme1, resolved_at=base + timedelta(minutes=4))
    # Tournament 2: W W W -> best run here is 3 (the overall best).
    t2 = await _make_tournament(db_session, me, name="T2", state="finished")
    pme2 = await _make_participant(db_session, t2, me)
    popp2 = await _make_participant(db_session, t2, opp)
    await _make_match(db_session, t2, pme2, popp2, winner=pme2, resolved_at=base + timedelta(minutes=5))
    await _make_match(db_session, t2, pme2, popp2, winner=pme2, resolved_at=base + timedelta(minutes=6))
    await _make_match(db_session, t2, pme2, popp2, winner=pme2, resolved_at=base + timedelta(minutes=7))

    stats = await stats_service.get_stats(db_session, me)
    assert stats.best_streak == 3
    # Streak is associated with the tournament of the LAST win of the run (T2).
    assert stats.streak_tournament_id == t2.id
    assert stats.streak_tournament_name == "T2"


@pytest.mark.asyncio
async def test_best_streak_zero_and_no_tournament_when_no_wins(db_session):
    me = await _make_user(db_session, "me")
    stats = await stats_service.get_stats(db_session, me)
    assert stats.best_streak == 0
    assert stats.streak_tournament_id is None
    assert stats.streak_tournament_name is None


# --- friends count (FR-025) ----------------------------------------------


@pytest.mark.asyncio
async def test_friends_count_accepted_both_directions_excludes_deleted(db_session):
    me = await _make_user(db_session, "me")
    a = await _make_user(db_session, "a")
    b = await _make_user(db_session, "b")
    c = await _make_user(db_session, "c")
    gone = await _make_user(db_session, "gone", deleted=True)
    # accepted where I'm the requester
    db_session.add(Friendship(requester_id=me.id, addressee_id=a.id, status="accepted"))
    # accepted where I'm the addressee
    db_session.add(Friendship(requester_id=b.id, addressee_id=me.id, status="accepted"))
    # pending -> not a friend
    db_session.add(Friendship(requester_id=me.id, addressee_id=c.id, status="pending"))
    # accepted but the other user is anonymized -> excluded
    db_session.add(Friendship(requester_id=me.id, addressee_id=gone.id, status="accepted"))
    await db_session.flush()

    stats = await stats_service.get_stats(db_session, me)
    assert stats.friends_count == 2


# --- empty user (FR-008, SC-003) -----------------------------------------


@pytest.mark.asyncio
async def test_brand_new_user_all_neutral_no_error(db_session):
    me = await _make_user(db_session, "fresh")
    stats = await stats_service.get_stats(db_session, me)
    assert stats.active_tournaments == 0
    assert stats.weekly_delta is None
    assert stats.total_wins == 0
    assert stats.games_played == 0
    assert stats.winrate is None
    assert stats.best_streak == 0
    assert stats.streak_tournament_id is None
    assert stats.streak_tournament_name is None
    assert stats.friends_count == 0
