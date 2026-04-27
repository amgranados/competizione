"""Riot API client Protocol and factory.

Iteration 003 (edit-profile) extends the Protocol with profile-related methods
and wires HttpRiotAPIClient as the production implementation when RIOT_API_KEY
is set. Iteration 002's match-verification methods are kept untouched.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# ----- 002 dataclasses (kept verbatim) ------------------------------------

@dataclass(frozen=True)
class ParticipantInfo:
    """Minimal info about one player in a Riot match."""

    puuid: str
    team_id: int


@dataclass(frozen=True)
class MatchResult:
    """Data returned by Riot for a tournament-code match."""

    participants: list[ParticipantInfo]
    duration_seconds: int
    game_mode: str
    start_timestamp: datetime


# ----- 003 dataclasses (profile / LoL stats) ------------------------------

@dataclass(frozen=True)
class SummonerProfile:
    summoner_level: int
    region: str
    profile_icon_id: int = 0


@dataclass(frozen=True)
class RankedEntry:
    queue_type: str  # "RANKED_SOLO_5x5" | "RANKED_FLEX_SR"
    tier: str
    rank: str
    league_points: int
    wins: int
    losses: int


@dataclass(frozen=True)
class RankedStats:
    solo_duo: RankedEntry | None = None
    flex: RankedEntry | None = None


@dataclass(frozen=True)
class ChampionMastery:
    champion_id: int
    champion_level: int
    champion_points: int


@dataclass(frozen=True)
class MatchSummary:
    match_id: str
    played_at: datetime
    duration_seconds: int
    champion_id: int
    kills: int
    deaths: int
    assists: int
    win: bool
    queue: str


# ----- 003 exceptions -----------------------------------------------------

class RiotIdentityError(Exception):
    """Riot rejected the identity (4xx). Used for resolve_puuid + 4xx wrappers."""


class RiotUnavailableError(Exception):
    """Riot returned 5xx, timeout or connection error."""


# ----- Protocol -----------------------------------------------------------

@runtime_checkable
class RiotAPIClient(Protocol):
    # 002 (kept; verification path remains DEFER for tournaments)
    def validate_riot_id(self, game_name: str, tag_line: str) -> bool: ...

    def get_match_by_tournament_code(self, tournament_code: str) -> MatchResult | None: ...

    # 003 — profile / LoL stats
    async def resolve_puuid(self, game_name: str, tag_line: str, region: str) -> str: ...

    async def get_summoner_profile(self, puuid: str, region: str) -> SummonerProfile: ...

    async def get_ranked_stats(self, puuid: str, region: str) -> RankedStats: ...

    async def get_champion_mastery(
        self, puuid: str, region: str, limit: int = 5
    ) -> list[ChampionMastery]: ...

    async def get_recent_matches(
        self, puuid: str, region: str, limit: int = 5
    ) -> list[MatchSummary]: ...


def get_riot_api_client(settings) -> RiotAPIClient:
    """Return a Riot API client based on RIOT_API_KEY presence.

    - RIOT_API_KEY unset → MockRiotAPIClient with explicit INFO log.
    - RIOT_API_KEY set   → HttpRiotAPIClient (003 wiring).
    """
    from app.services.riot_api.mock_client import MockRiotAPIClient

    if getattr(settings, "RIOT_API_KEY", None) is None:
        logger.info("Using MockRiotAPIClient: RIOT_API_KEY not set")
        return MockRiotAPIClient()

    from app.services.riot_api.http_client import HttpRiotAPIClient

    return HttpRiotAPIClient(api_key=settings.RIOT_API_KEY)
