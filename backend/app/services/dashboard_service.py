"""Dashboard service (005-user-dashboard).

Orchestrates the single `GET /api/dashboard` response: greeting + fixed subtitle
+ stat cards (`stats_service`) + "Mis torneos" (this module) + recent activity
(`activity_service`). Everything is derived from the authenticated user; no
endpoint or query ever accepts an external `user_id` (FR-023).
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.match import Match
from app.models.participant import Participant
from app.models.tournament import Tournament
from app.models.user import User
from app.schemas.dashboard import (
    ActiveTournamentsStat,
    ActivityEvent,
    ActorRef,
    DashboardResponse,
    StatsCards,
    StreakStat,
    TournamentCard,
    TournamentRef,
    WinsStat,
)
from app.services import activity_service, stats_service
from app.services.stats_service import IN_PROGRESS_STATES

# Tournaments shown in "Mis torneos": in progress (either domain token, see
# IN_PROGRESS_STATES / research.md Decisión 2) or with open registration.
MY_TOURNAMENT_STATES = (*IN_PROGRESS_STATES, "open")

# Fixed subtitle, identical for every user (FR-002). Wording is product's choice
# (spec Assumption); this feature only guarantees its presence.
SUBTITLE = "Tu centro de operaciones competitivo"

# Safe greeting fallback if a user somehow has no nickname (edge case, FR-001).
_GREETING_FALLBACK = "jugador"


async def get_my_tournaments(session: AsyncSession, user: User) -> list[TournamentCard]:
    """Tournaments the user participates in (not removed) that are `in_progress`
    or `open` (FR-009/010). Each card carries players_count and, for in_progress,
    the current round (max `round_number` among its matches); for open, start_at.
    """
    # players_count per tournament (active participants only).
    players_sub = (
        select(
            Participant.tournament_id.label("tid"),
            func.count().label("players_count"),
        )
        .where(Participant.removed.is_(False))
        .group_by(Participant.tournament_id)
        .subquery()
    )
    # current round = highest round_number among the tournament's matches.
    rounds_sub = (
        select(
            Match.tournament_id.label("tid"),
            func.max(Match.round_number).label("current_round"),
        )
        .group_by(Match.tournament_id)
        .subquery()
    )

    stmt = (
        select(
            Tournament,
            func.coalesce(players_sub.c.players_count, 0),
            rounds_sub.c.current_round,
        )
        .join(
            Participant,
            (Participant.tournament_id == Tournament.id)
            & (Participant.user_id == user.id)
            & (Participant.removed.is_(False)),
        )
        .outerjoin(players_sub, players_sub.c.tid == Tournament.id)
        .outerjoin(rounds_sub, rounds_sub.c.tid == Tournament.id)
        .where(Tournament.state.in_(MY_TOURNAMENT_STATES))
        .order_by(Tournament.start_at.is_(None), Tournament.start_at.asc(), Tournament.name.asc())
    )

    rows = (await session.execute(stmt)).all()
    cards: list[TournamentCard] = []
    for tournament, players_count, current_round in rows:
        is_in_progress = tournament.state in IN_PROGRESS_STATES
        # Normalize the domain token ("active") to the contract token
        # ("in_progress") so the response enum {in_progress, open} always holds.
        state = "in_progress" if is_in_progress else tournament.state
        cards.append(
            TournamentCard(
                id=tournament.id,
                name=tournament.name,
                state=state,
                format=tournament.format,
                players_count=int(players_count or 0),
                current_round=current_round if is_in_progress else None,
                start_at=tournament.start_at if not is_in_progress else None,
            )
        )
    return cards


def _stats_to_schema(stats: stats_service.StatsResult) -> StatsCards:
    return StatsCards(
        active_tournaments=ActiveTournamentsStat(
            count=stats.active_tournaments, weekly_delta=stats.weekly_delta
        ),
        total_wins=WinsStat(
            wins=stats.total_wins, games_played=stats.games_played, winrate=stats.winrate
        ),
        best_streak=StreakStat(
            best=stats.best_streak,
            tournament_id=stats.streak_tournament_id,
            tournament_name=stats.streak_tournament_name,
        ),
        friends_count=stats.friends_count,
    )


def _activity_to_schema(entries: list[activity_service.ActivityEntry]) -> list[ActivityEvent]:
    events: list[ActivityEvent] = []
    for e in entries:
        tournament = (
            TournamentRef(id=e.tournament_id, name=e.tournament_name)
            if e.tournament_name is not None
            else None
        )
        events.append(
            ActivityEvent(
                id=e.id,
                event_type=e.event_type,
                created_at=e.created_at,
                actor=ActorRef(
                    id=e.actor_id,
                    nickname=e.actor_nickname,
                    avatar_url=e.actor_avatar_url,
                    exists=e.actor_exists,
                ),
                tournament=tournament,
            )
        )
    return events


async def build_dashboard(session: AsyncSession, user: User) -> DashboardResponse:
    """Compose the full dashboard for the authenticated user (FR-024).

    All sections derive from `user`; no external `user_id` is accepted (FR-023).
    """
    nickname = user.nickname or _GREETING_FALLBACK
    stats = await stats_service.get_stats(session, user)
    my_tournaments = await get_my_tournaments(session, user)
    activity = await activity_service.list_recent(session, user)
    return DashboardResponse(
        greeting=f"Hola, {nickname}",
        subtitle=SUBTITLE,
        stats=_stats_to_schema(stats),
        my_tournaments=my_tournaments,
        activity=_activity_to_schema(activity),
    )
