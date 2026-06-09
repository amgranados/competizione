"""Pydantic schemas for GET /api/dashboard (005-user-dashboard).

Mirrors `specs/005-user-dashboard/contracts/dashboard.openapi.yaml`. Built up
across tasks: US1 stat cards (this block), US2 `TournamentCard`, US3
`ActivityEvent`/`ActorRef`/`TournamentRef`, and the top-level `DashboardResponse`.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# --- US1: stat cards (FR-003..006, FR-025) -------------------------------


class ActiveTournamentsStat(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    count: int = Field(ge=0)
    # null => no history / brand-new user (neutral, not a misleading number).
    weekly_delta: int | None = None


class WinsStat(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    wins: int = Field(ge=0)
    games_played: int = Field(ge=0)
    # null or 0 when games_played == 0 (FR-008, no division by zero).
    winrate: float | None = Field(default=None, ge=0, le=100)


class StreakStat(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    best: int = Field(ge=0)
    # Tournament of the streak's last win; null when best == 0.
    tournament_id: uuid.UUID | None = None
    tournament_name: str | None = None


class StatsCards(BaseModel):
    """The four metric cards (FR-003..FR-006, FR-025)."""

    active_tournaments: ActiveTournamentsStat
    total_wins: WinsStat
    best_streak: StreakStat
    friends_count: int = Field(ge=0)


# --- US2: my tournaments (FR-009..FR-012) --------------------------------


class TournamentCard(BaseModel):
    """A card in the "Mis torneos" section. Only `in_progress` or `open`
    tournaments the user participates in are ever listed (FR-010)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    state: Literal["in_progress", "open"]
    format: Literal["round_robin", "single_elim"]
    players_count: int = Field(ge=0)
    # Present for in_progress (FR-012).
    current_round: int | None = None
    # Present/relevant for open (FR-012).
    start_at: datetime | None = None


# --- US3: activity feed (FR-015..FR-022) ---------------------------------


class ActorRef(BaseModel):
    """Clickable reference to the event's actor (FR-018). `exists=false` =>
    the client renders the nickname without a link (FR-022)."""

    id: uuid.UUID | None = None
    nickname: str
    avatar_url: str | None = None
    exists: bool = True


class TournamentRef(BaseModel):
    """Clickable reference to the linked tournament (FR-018). `id=None` =>
    render without a link (FR-022, deleted tournament)."""

    id: uuid.UUID | None = None
    name: str


class ActivityEvent(BaseModel):
    id: uuid.UUID
    event_type: Literal[
        "MATCH_WIN", "TOURNAMENT_JOIN", "TOURNAMENT_INVITE", "TOURNAMENT_CREATE"
    ]
    created_at: datetime
    actor: ActorRef
    # null when the event references no tournament or it was deleted (FR-022).
    tournament: TournamentRef | None = None


# --- Top-level response (FR-024) -----------------------------------------


class DashboardResponse(BaseModel):
    """The complete dashboard in a single response (FR-024, SC-001)."""

    greeting: str
    subtitle: str
    stats: StatsCards
    my_tournaments: list[TournamentCard]
    activity: list[ActivityEvent]
