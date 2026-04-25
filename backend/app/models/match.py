from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tournament_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tournaments.id", ondelete="CASCADE"), index=True, nullable=False
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    bracket_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    player1_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("participants.id", ondelete="CASCADE"), nullable=False
    )
    player2_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("participants.id", ondelete="CASCADE"), nullable=True
    )
    is_bye: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tournament_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    code_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    state: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    winner_participant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("participants.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
