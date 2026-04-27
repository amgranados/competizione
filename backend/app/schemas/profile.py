"""Pydantic schemas for /api/profile endpoints (003-edit-profile)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, StringConstraints

from app.services.riot_api.regions import PlatformRegion


# --- Inputs --------------------------------------------------------------

class UpdateNickname(BaseModel):
    nickname: Annotated[
        str,
        StringConstraints(pattern=r"^[A-Za-z]+$", min_length=1, max_length=32),
    ]


class UpdatePassword(BaseModel):
    current_password: Annotated[str, Field(min_length=1, max_length=128)]
    new_password: Annotated[str, Field(min_length=8, max_length=128)]


class UpdateAvatar(BaseModel):
    avatar_url: HttpUrl | None = None


class LinkRiotAccount(BaseModel):
    game_name: Annotated[str, Field(min_length=1, max_length=64)]
    tag_line: Annotated[str, Field(min_length=1, max_length=16)]
    region: PlatformRegion


class DeleteAccountConfirm(BaseModel):
    confirmation: Annotated[str, Field(min_length=1, max_length=64)]


# --- Outputs -------------------------------------------------------------

class ChampionMasteryEntry(BaseModel):
    champion_id: int
    champion_name: str
    champion_level: int
    champion_points: int
    image_url: str = ""


class LinkedGameSummary(BaseModel):
    game: Literal["lol"] = "lol"
    game_name: str
    tag_line: str
    region: PlatformRegion
    linked_at: datetime
    summoner_level: int | None = None
    profile_icon_id: int | None = None
    profile_icon_url: str | None = None
    summoner_unavailable: bool = False
    masteries: list[ChampionMasteryEntry] = Field(default_factory=list)
    masteries_unavailable: bool = False


class ProfileBasic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nickname: str
    email: EmailStr | None = None
    avatar_url: str | None = None
    linked_games: list[LinkedGameSummary] = Field(default_factory=list)


class ProfileResponse(ProfileBasic):
    pass
