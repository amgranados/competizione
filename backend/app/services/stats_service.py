"""Stats service (005-user-dashboard, US1).

Computes the four dashboard stat cards hot from the authenticated user's own
history — no cache, no stored snapshot (FR-007, research.md Decisión 5):

1. Active tournaments (`state='in_progress'` where the user is an active
   participant) + weekly delta vs 7 days ago.
2. Total wins (excluding byes) + games_played + winrate (0/None, never a
   ZeroDivision — FR-008).
3. Best streak: longest run of consecutive wins within a single tournament,
   associated with the tournament of the run's LAST win (Assumption).
4. Friends count: accepted friendships in either direction, excluding
   anonymized users (FR-025, reuses the `_pair_filter` idea from friends_service).

`get_stats` never accepts an external `user_id`: it operates on the passed-in
authenticated `User` (FR-023).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.friendship import Friendship
from app.models.match import Match
from app.models.participant import Participant
from app.models.tournament import Tournament
from app.models.user import User

# State-token reconciliation (research.md Decisión 2, T030): the dashboard
# contract token for "en curso" is `in_progress`, but the existing domain
# (`tournament_service.start_tournament`) sets `state="active"` and the
# `TournamentState` enum defines `ACTIVE = "active"`. Rather than change the
# domain transition (which requires human approval — Constitution III/IV), the
# dashboard read layer treats BOTH tokens as "in progress".
IN_PROGRESS_STATES = ("in_progress", "active")


@dataclass
class StatsResult:
    active_tournaments: int
    weekly_delta: int | None
    total_wins: int
    games_played: int
    winrate: float | None
    best_streak: int
    streak_tournament_id: uuid.UUID | None
    streak_tournament_name: str | None
    friends_count: int


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime | None) -> datetime | None:
    """Coerce naive datetimes (loaded from SQLite) to UTC-aware for comparison."""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


async def _active_tournaments_count(session: AsyncSession, user_id: uuid.UUID) -> int:
    stmt = (
        select(func.count(func.distinct(Tournament.id)))
        .join(Participant, Participant.tournament_id == Tournament.id)
        .where(
            Participant.user_id == user_id,
            Participant.removed.is_(False),
            Tournament.state.in_(IN_PROGRESS_STATES),
        )
    )
    return int((await session.execute(stmt)).scalar_one() or 0)


async def _weekly_delta(
    session: AsyncSession, user_id: uuid.UUID, active_now: int
) -> int | None:
    """active_now − (tournaments that were running 7 days ago).

    There is no stored state history, so "running 7 days ago" is approximated
    from the tournament's own timestamps (research.md Decisión 5): the user
    participated, the tournament had started by then (`started_at <= now-7d`)
    and had not finished by then (`finished_at IS NULL OR finished_at > now-7d`).

    Returns None when the user has no tournament participation history at all —
    a neutral indicator rather than a misleading number (edge case, spec).
    """
    participates_stmt = (
        select(func.count())
        .select_from(Participant)
        .where(Participant.user_id == user_id, Participant.removed.is_(False))
    )
    if int((await session.execute(participates_stmt)).scalar_one() or 0) == 0:
        return None

    cutoff = _now() - timedelta(days=7)
    rows = (
        await session.execute(
            select(Tournament.started_at, Tournament.finished_at)
            .join(Participant, Participant.tournament_id == Tournament.id)
            .where(Participant.user_id == user_id, Participant.removed.is_(False))
        )
    ).all()
    active_then = 0
    for started_at, finished_at in rows:
        started_at = _as_utc(started_at)
        finished_at = _as_utc(finished_at)
        if started_at is not None and started_at <= cutoff and (
            finished_at is None or finished_at > cutoff
        ):
            active_then += 1
    return active_now - active_then


async def _wins_and_games(
    session: AsyncSession, user_id: uuid.UUID
) -> tuple[int, int]:
    """(wins, games_played) over the user's decided, non-bye matches.

    Reuses the Match→Participant→User join pattern from standings_service: a
    match counts if the user is one of its two players, it is not a bye and it
    is decided (`state != 'pending'` and a winner is set). A win is one where
    the winner participant belongs to the user.
    """
    my_participant_ids = (
        select(Participant.id).where(Participant.user_id == user_id).scalar_subquery()
    )
    decided = and_(
        Match.is_bye.is_(False),
        Match.state != "pending",
        Match.winner_participant_id.is_not(None),
    )
    played = and_(
        decided,
        or_(
            Match.player1_id.in_(my_participant_ids),
            Match.player2_id.in_(my_participant_ids),
        ),
    )
    games_played = int(
        (await session.execute(select(func.count()).select_from(Match).where(played))).scalar_one()
        or 0
    )
    wins = int(
        (
            await session.execute(
                select(func.count())
                .select_from(Match)
                .where(decided, Match.winner_participant_id.in_(my_participant_ids))
            )
        ).scalar_one()
        or 0
    )
    return wins, games_played


async def _best_streak(
    session: AsyncSession, user_id: uuid.UUID
) -> tuple[int, uuid.UUID | None, str | None]:
    """Longest run of consecutive wins inside a single tournament.

    Matches are grouped per tournament and ordered by `resolved_at`; a win
    extends the run, any decided loss resets it. The returned tournament ref is
    the one of the LAST win of the best run (deterministic, Assumption). Only
    decided, non-bye matches are considered.
    """
    my_participant_ids = (
        select(Participant.id).where(Participant.user_id == user_id).scalar_subquery()
    )
    stmt = (
        select(
            Match.tournament_id,
            Match.resolved_at,
            Match.winner_participant_id.in_(my_participant_ids).label("is_win"),
            Tournament.name,
        )
        .join(Tournament, Tournament.id == Match.tournament_id)
        .where(
            Match.is_bye.is_(False),
            Match.state != "pending",
            Match.winner_participant_id.is_not(None),
            or_(
                Match.player1_id.in_(my_participant_ids),
                Match.player2_id.in_(my_participant_ids),
            ),
        )
    )
    rows = (await session.execute(stmt)).all()

    # Group by tournament, then walk each in resolved_at order.
    by_tournament: dict[uuid.UUID, list[tuple[datetime, bool, str]]] = {}
    for tournament_id, resolved_at, is_win, name in rows:
        by_tournament.setdefault(tournament_id, []).append(
            (_as_utc(resolved_at) or datetime.min.replace(tzinfo=timezone.utc), bool(is_win), name)
        )

    best = 0
    best_tid: uuid.UUID | None = None
    best_name: str | None = None
    for tournament_id, entries in by_tournament.items():
        entries.sort(key=lambda e: e[0])
        run = 0
        for _resolved_at, is_win, name in entries:
            if is_win:
                run += 1
                if run > best:
                    best = run
                    best_tid = tournament_id
                    best_name = name
            else:
                run = 0
    return best, best_tid, best_name


async def _friends_count(session: AsyncSession, user_id: uuid.UUID) -> int:
    """COUNT of accepted friendships in either direction, excluding the user
    and any anonymized counterpart (`deleted_at IS NOT NULL`)."""
    other_id = func.coalesce(
        func.nullif(Friendship.requester_id, user_id), Friendship.addressee_id
    )
    stmt = (
        select(func.count())
        .select_from(Friendship)
        .join(User, User.id == other_id)
        .where(
            Friendship.status == "accepted",
            or_(
                Friendship.requester_id == user_id,
                Friendship.addressee_id == user_id,
            ),
            User.deleted_at.is_(None),
        )
    )
    return int((await session.execute(stmt)).scalar_one() or 0)


async def get_stats(session: AsyncSession, user: User) -> StatsResult:
    """Compute all four stat cards for the authenticated user (FR-003..006/025)."""
    active = await _active_tournaments_count(session, user.id)
    weekly_delta = await _weekly_delta(session, user.id, active)
    wins, games = await _wins_and_games(session, user.id)
    winrate = (wins / games * 100.0) if games > 0 else None
    best, streak_tid, streak_name = await _best_streak(session, user.id)
    friends = await _friends_count(session, user.id)
    return StatsResult(
        active_tournaments=active,
        weekly_delta=weekly_delta,
        total_wins=wins,
        games_played=games,
        winrate=winrate,
        best_streak=best,
        streak_tournament_id=streak_tid,
        streak_tournament_name=streak_name,
        friends_count=friends,
    )
