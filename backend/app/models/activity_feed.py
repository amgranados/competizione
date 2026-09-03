"""ActivityFeed — an activity event written at the moment the action happens
(005-user-dashboard, research.md Decisión 3).

A row records that `actor_id` performed `event_type`, optionally referencing a
tournament. The dashboard feed reads the most recent rows whose actor is the
current user or an accepted friend (FR-019), newest first, limited to 6.

Design notes:
- `actor_id` FK → users ON DELETE CASCADE: when a user is hard-deleted their
  events disappear with them.
- `tournament_id` FK → tournaments ON DELETE SET NULL (nullable): the actor's
  event survives the tournament being deleted; the feed then renders it without
  a tournament link (FR-022, Decisión 7).
- `event_type` is a non-native Enum (`native_enum=False, create_constraint=True`),
  same style as `friendship_status` in friendship.py, so it decays to a
  VARCHAR + CHECK constraint on SQLite and PostgreSQL alike.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ActivityFeed(Base):
    __tablename__ = "activity_feed"
    __table_args__ = (
        Index("idx_activity_actor_created", "actor_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(
        Enum(
            "MATCH_WIN",
            "TOURNAMENT_JOIN",
            "TOURNAMENT_INVITE",
            "TOURNAMENT_CREATE",
            name="activity_event_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    tournament_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tournaments.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
