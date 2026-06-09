"""Activity service (005-user-dashboard, US3).

Two responsibilities (research.md Decisión 3):

- `record(...)`: write one activity event at the moment the action happens.
  Called additively from match_service/tournament_service.
- `list_recent(...)`: read the ≤6 most recent events visible to the user — own
  events plus those of accepted friends — newest first, resilient to deleted
  tournaments (FR-015..FR-022).

Visibility (FR-019): an event is visible if its actor is the current user or an
accepted friend whose account is still active (`deleted_at IS NULL`). The actor
join is therefore an INNER join on a non-anonymized user; the tournament join is
a LEFT join so an event whose tournament was deleted (`tournament_id` NULL) is
still returned without a link (FR-022).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.activity_feed import ActivityFeed
from app.models.friendship import Friendship
from app.models.tournament import Tournament
from app.models.user import User

FEED_LIMIT = 6

EventType = str  # one of MATCH_WIN | TOURNAMENT_JOIN | TOURNAMENT_INVITE | TOURNAMENT_CREATE


@dataclass
class ActivityEntry:
    id: uuid.UUID
    event_type: str
    created_at: datetime
    actor_id: uuid.UUID | None
    actor_nickname: str
    actor_avatar_url: str | None
    actor_exists: bool
    tournament_id: uuid.UUID | None
    tournament_name: str | None


async def record(
    session: AsyncSession,
    *,
    actor_id: uuid.UUID,
    event_type: EventType,
    tournament_id: uuid.UUID | None = None,
) -> ActivityFeed:
    """Insert one activity event. Flushes (no commit) so it participates in the
    caller's transaction — the instrumented services commit/flush themselves."""
    event = ActivityFeed(
        actor_id=actor_id,
        event_type=event_type,
        tournament_id=tournament_id,
    )
    session.add(event)
    await session.flush()
    return event


async def list_recent(
    session: AsyncSession, user: User, limit: int = FEED_LIMIT
) -> list[ActivityEntry]:
    """Return up to `limit` events visible to `user`, newest first."""
    # Accepted friends in either direction → the "other" user id.
    friends_stmt = select(
        Friendship.requester_id, Friendship.addressee_id
    ).where(
        Friendship.status == "accepted",
        or_(
            Friendship.requester_id == user.id,
            Friendship.addressee_id == user.id,
        ),
    )
    friend_ids: set[uuid.UUID] = set()
    for requester_id, addressee_id in (await session.execute(friends_stmt)).all():
        friend_ids.add(addressee_id if requester_id == user.id else requester_id)

    visible_ids = {user.id, *friend_ids}

    actor = aliased(User)
    stmt = (
        select(
            ActivityFeed.id,
            ActivityFeed.event_type,
            ActivityFeed.created_at,
            actor.id,
            actor.nickname,
            actor.avatar_url,
            Tournament.id,
            Tournament.name,
        )
        # INNER join on a non-anonymized actor (anonymized friends drop out, FR-019).
        .join(actor, and_(actor.id == ActivityFeed.actor_id, actor.deleted_at.is_(None)))
        # LEFT join on tournament so deleted-tournament events stay resilient (FR-022).
        .outerjoin(Tournament, Tournament.id == ActivityFeed.tournament_id)
        .where(ActivityFeed.actor_id.in_(visible_ids))
        .order_by(ActivityFeed.created_at.desc(), ActivityFeed.id.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    return [
        ActivityEntry(
            id=row[0],
            event_type=row[1],
            created_at=row[2],
            actor_id=row[3],
            actor_nickname=row[4],
            actor_avatar_url=row[5],
            actor_exists=True,
            tournament_id=row[6],
            tournament_name=row[7],
        )
        for row in rows
    ]
