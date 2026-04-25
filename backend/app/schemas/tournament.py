from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class TournamentFormat(str, Enum):
    ROUND_ROBIN = "round_robin"
    SINGLE_ELIM = "single_elim"


class TournamentState(str, Enum):
    DRAFT = "draft"
    OPEN = "open"
    ACTIVE = "active"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class InvitationState(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class MatchState(str, Enum):
    PENDING = "pending"
    MANUAL = "manual"
    # "verified_api" reserved for future iteration — not accepted by any endpoint yet


class TournamentCreate(BaseModel):
    name: Annotated[str, StringConstraints(min_length=1, max_length=100, strip_whitespace=True)]
    start_at: datetime | None = None
    format: TournamentFormat


class TournamentUpdate(BaseModel):
    name: Annotated[str, StringConstraints(min_length=1, max_length=100, strip_whitespace=True)] | None = None
    start_at: datetime | None = None
    format: TournamentFormat | None = None


class ParticipantSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    nickname: str | None = None
    accepted_at: datetime


class Tournament(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    start_at: datetime | None = None
    format: TournamentFormat
    state: TournamentState
    organizer_id: uuid.UUID
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    cancelled_at: datetime | None = None
    participants: list[ParticipantSummary] = Field(default_factory=list)


class InvitationCreate(BaseModel):
    invited_user_id: uuid.UUID


class Invitation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tournament_id: uuid.UUID
    invited_user_id: uuid.UUID
    inviter_user_id: uuid.UUID
    state: InvitationState
    created_at: datetime
    expires_at: datetime
    responded_at: datetime | None = None


class RoundMatchSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    round_number: int
    bracket_position: int | None = None
    player1_id: uuid.UUID
    player2_id: uuid.UUID | None = None
    is_bye: bool
    tournament_code: str | None = None
    state: MatchState
    winner_participant_id: uuid.UUID | None = None


class RoundView(BaseModel):
    number: int
    matches: list[RoundMatchSummary]


class Schedule(BaseModel):
    format: TournamentFormat
    rounds: list[RoundView]


class StandingEntry(BaseModel):
    participant_id: uuid.UUID
    user_id: uuid.UUID
    nickname: str | None = None
    wins: int
    losses: int
    byes: int
    points: int
    rank: int
