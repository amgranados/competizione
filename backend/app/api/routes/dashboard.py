"""HTTP route for GET /api/dashboard (005-user-dashboard).

A single authenticated endpoint that returns the whole dashboard
(`DashboardResponse`) computed hot for the current user. It never accepts an
external `user_id`: it always operates on the session user (FR-023).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_current_user
from app.db.base import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardResponse
from app.services import dashboard_service

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    return await dashboard_service.build_dashboard(session, current_user)
