"""Pydantic schemas for /api/profile endpoints (003-edit-profile)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    StringConstraints,
    field_validator,
)

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

    @field_validator("game_name", "tag_line")
    @classmethod
    def _no_path_or_control_chars(cls, v: str) -> str:
        """L-02 (defensa en profundidad): un Riot ID válido no contiene barras
        ni caracteres de control. Esto, junto al url-encoding en el cliente HTTP,
        impide manipular la ruta del endpoint de Riot. NO restringimos el resto
        del juego de caracteres (los Riot ID admiten espacios y unicode)."""
        if "/" in v or "\\" in v:
            raise ValueError("Riot ID no puede contener barras")
        if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in v):
            raise ValueError("Riot ID no puede contener caracteres de control")
        return v


class DeleteAccountConfirm(BaseModel):
    confirmation: Annotated[str, Field(min_length=1, max_length=64)]


# --- Outputs -------------------------------------------------------------

class ChampionMasteryEntry(BaseModel):
    champion_id: int
    champion_name: str
    champion_level: int
    champion_points: int
    image_url: str = ""


class RankedQueueEntry(BaseModel):
    queue_type: Literal["RANKED_SOLO_5x5", "RANKED_FLEX_SR"]
    tier: str
    rank: str
    league_points: int
    wins: int
    losses: int


class RecentMatchEntry(BaseModel):
    match_id: str
    played_at: datetime
    duration_seconds: int
    champion_id: int
    champion_name: str
    champion_image_url: str = ""
    kills: int
    deaths: int
    assists: int
    win: bool
    queue: str


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
    ranked_solo: RankedQueueEntry | None = None
    ranked_flex: RankedQueueEntry | None = None
    ranked_unavailable: bool = False
    recent_matches: list[RecentMatchEntry] = Field(default_factory=list)
    recent_matches_unavailable: bool = False


class ProfileBasic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nickname: str
    email: EmailStr | None = None
    avatar_url: str | None = None
    linked_games: list[LinkedGameSummary] = Field(default_factory=list)


class ProfileResponse(ProfileBasic):
    pass
