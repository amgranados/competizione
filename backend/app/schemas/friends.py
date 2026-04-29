"""Pydantic schemas for /api/friends endpoints (004-add-friends)."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.schemas.profile import LinkedGameSummary


class FriendshipStatus(str, Enum):
    """Relationship status of the authenticated user vs a target user (HD-1)."""

    SIN_RELACION = "SIN_RELACION"
    PENDIENTE_ENVIADA = "PENDIENTE_ENVIADA"
    PENDIENTE_RECIBIDA = "PENDIENTE_RECIBIDA"
    AMIGO = "AMIGO"


class UserSearchResult(BaseModel):
    """One row of the search response. The `relationship_status` is computed
    server-side so the frontend never has to infer it from a separate cache.
    `pending_request_id` is only populated when there is a pending row between
    the two users; the frontend uses it to accept/reject inline if needed.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nickname: str
    avatar_url: HttpUrl | None = None
    relationship_status: FriendshipStatus
    pending_request_id: uuid.UUID | None = None


class FriendRequestResponse(BaseModel):
    """Returned by POST /friends/request/{user_id} and listed by
    GET /friends/requests."""

    id: uuid.UUID
    requester_id: uuid.UUID
    addressee_id: uuid.UUID
    requester_nickname: str
    requester_avatar_url: HttpUrl | None = None
    created_at: datetime


class FriendRequestActionResult(BaseModel):
    """Returned after accept/reject of a pending request."""

    request_id: uuid.UUID
    action: Literal["accepted", "rejected"]
    relationship_status: FriendshipStatus


class PublicProfileResponse(BaseModel):
    """Profile of another user. Reuses the LoL composition from 003 but omits
    `email` and never exposes edit controls. Adds the `relationship_status`
    field (HD-1) so the FriendshipButton can render in the same payload.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nickname: str
    avatar_url: str | None = None
    linked_games: list[LinkedGameSummary] = Field(default_factory=list)
    relationship_status: FriendshipStatus
    pending_request_id: uuid.UUID | None = None
