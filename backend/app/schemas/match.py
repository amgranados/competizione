from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.tournament import MatchState


class Match(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tournament_id: uuid.UUID
    round_number: int
    bracket_position: int | None = None
    player1_id: uuid.UUID
    player2_id: uuid.UUID | None = None
    is_bye: bool
    tournament_code: str | None = None
    code_created_at: datetime | None = None
    state: MatchState
    winner_participant_id: uuid.UUID | None = None
    resolved_at: datetime | None = None


class ManualResultRequest(BaseModel):
    winner_participant_id: uuid.UUID
