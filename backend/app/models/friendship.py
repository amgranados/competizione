"""Friendship — directional row representing a pending request or an accepted
friendship between two users (004-add-friends).

A single row represents the relationship between two users in any state.
- `status='pending'`: directional request from `requester_id` to `addressee_id`.
- `status='accepted'`: bidirectional friendship between the two users.

Constraints:
- `UNIQUE (requester_id, addressee_id)`: a directional row cannot duplicate.
- `CHECK (requester_id <> addressee_id)`: defense-in-depth for FR-014
  (a user cannot befriend themselves).

The cross-direction race (A->B and B->A submitted simultaneously) is handled
in the service layer with `SELECT ... FOR UPDATE` (HD-3).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Friendship(Base):
    __tablename__ = "friendships"
    __table_args__ = (
        UniqueConstraint("requester_id", "addressee_id", name="uq_friendship_pair"),
        CheckConstraint("requester_id <> addressee_id", name="ck_friendship_no_self"),
        Index("idx_friendships_requester", "requester_id", "status"),
        Index("idx_friendships_addressee", "addressee_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requester_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    addressee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Enum(
            "pending",
            "accepted",
            name="friendship_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
