from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class NotificationType(str, Enum):
    INVITATION_RECEIVED = "invitation_received"
    INVITATION_CANCELLED = "invitation_cancelled"
    INVITATION_ACCEPTED = "invitation_accepted"
    INVITATION_REJECTED = "invitation_rejected"
    TOURNAMENT_STARTED = "tournament_started"
    TOURNAMENT_CANCELLED = "tournament_cancelled"
    MATCH_GENERATED = "match_generated"
    MATCH_RESOLVED = "match_resolved"
    TOURNAMENT_FINISHED = "tournament_finished"
    FRIEND_REQUEST_RECEIVED = "friend_request_received"
    FRIEND_REQUEST_ACCEPTED = "friend_request_accepted"


class Notification(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    type: NotificationType
    tournament_id: uuid.UUID | None = None
    match_id: uuid.UUID | None = None
    invitation_id: uuid.UUID | None = None
    friendship_id: uuid.UUID | None = None
    created_at: datetime
    read_at: datetime | None = None
