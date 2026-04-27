"""RiotAccount — link between an internal user and a League of Legends account.

Stores the Riot ID (game_name + tag_line), the resolved PUUID and the
platform region (EUW1, NA1, KR, ...). The platform is needed to query
champion-mastery/v4, which lives on platform hosts (account/v1 lives on
continental hosts and is resolved separately via the platform→continent map).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RiotAccount(Base):
    __tablename__ = "riot_accounts"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_riot_account_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    puuid: Mapped[str] = mapped_column(String(78), unique=True, nullable=False, index=True)
    game_name: Mapped[str] = mapped_column(String(64), nullable=False)
    tag_line: Mapped[str] = mapped_column(String(16), nullable=False)
    region: Mapped[str] = mapped_column(String(8), nullable=False)
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
