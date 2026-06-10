from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Tournament(Base):
    __tablename__ = "tournaments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    format: Mapped[str] = mapped_column(String(20), nullable=False)  # round_robin | single_elim
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    organizer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Tournament-Stub-V5: ids devueltos por Riot al registrar el provider y el
    # torneo. NULL hasta que el torneo arranca (o si Riot no estaba disponible
    # y se usaron códigos locales de respaldo).
    riot_provider_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    riot_tournament_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
