from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_current_user
from app.db.base import get_db
from app.models.user import User
from app.schemas.notification import Notification as NotificationSchema
from app.services import notification_service

router = APIRouter(tags=["notifications"])


@router.get("/notifications", response_model=list[NotificationSchema])
async def list_notifications(
    unread: bool = Query(False),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[NotificationSchema]:
    notifications = await notification_service.list_for_user(
        session, current_user.id, only_unread=unread
    )
    return [NotificationSchema.model_validate(n) for n in notifications]


@router.patch("/notifications/{notification_id}/read", response_model=NotificationSchema)
async def mark_read(
    notification_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationSchema:
    try:
        notification = await notification_service.mark_read(session, notification_id, current_user.id)
    except notification_service.NotificationNotFound:
        raise HTTPException(status_code=404, detail="notification not found")
    await session.commit()
    return NotificationSchema.model_validate(notification)
