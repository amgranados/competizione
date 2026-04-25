"""Notification service — persistence + queries (US1 backbone)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


class NotificationNotFound(Exception):
    pass


async def create_notification(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    type: str,
    tournament_id: uuid.UUID | None = None,
    match_id: uuid.UUID | None = None,
    invitation_id: uuid.UUID | None = None,
) -> Notification:
    notif = Notification(
        user_id=user_id,
        type=type,
        tournament_id=tournament_id,
        match_id=match_id,
        invitation_id=invitation_id,
    )
    session.add(notif)
    await session.flush()
    return notif


async def list_for_user(
    session: AsyncSession, user_id: uuid.UUID, only_unread: bool = False
) -> Sequence[Notification]:
    stmt = select(Notification).where(Notification.user_id == user_id)
    if only_unread:
        stmt = stmt.where(Notification.read_at.is_(None))
    stmt = stmt.order_by(desc(Notification.created_at))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def mark_read(session: AsyncSession, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification:
    stmt = select(Notification).where(
        Notification.id == notification_id, Notification.user_id == user_id
    )
    result = await session.execute(stmt)
    notif = result.scalar_one_or_none()
    if notif is None:
        raise NotificationNotFound()
    if notif.read_at is None:
        notif.read_at = datetime.now(timezone.utc)
        await session.flush()
    return notif
