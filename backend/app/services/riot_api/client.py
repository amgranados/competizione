"""Riot API client Protocol and factory.

This iteration (feature 002) does NOT consume the client from any endpoint;
verification-by-API is out of scope (see specs/002-tournament-management/plan.md
§ Scope). The Protocol, the Mock implementation and the factory are prepared
so the future iteration can wire them up without structural changes.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ParticipantInfo:
    """Minimal info about one player in a Riot match."""

    puuid: str
    team_id: int


@dataclass(frozen=True)
class MatchResult:
    """Data returned by Riot for a tournament-code match.

    Fields sized to support FR-036 validations in the future iteration:
    both players present, opposite teams, start timestamp vs. code creation,
    duration >= 5 minutes, game mode CLASSIC.
    """

    participants: list[ParticipantInfo]
    duration_seconds: int
    game_mode: str
    start_timestamp: datetime


@runtime_checkable
class RiotAPIClient(Protocol):
    def validate_riot_id(self, game_name: str, tag_line: str) -> bool: ...

    def get_match_by_tournament_code(self, tournament_code: str) -> MatchResult | None: ...


def get_riot_api_client(settings) -> RiotAPIClient:
    """Return a Riot API client based on RIOT_API_KEY presence.

    - If RIOT_API_KEY is unset -> MockRiotAPIClient (with explicit INFO log).
    - If RIOT_API_KEY is set   -> HttpRiotAPIClient (DEFERRED: raises NotImplementedError
      in this iteration to keep the wiring explicit; no silent fallback).
    """
    from app.services.riot_api.mock_client import MockRiotAPIClient

    if getattr(settings, "RIOT_API_KEY", None) is None:
        logger.info("Using MockRiotAPIClient: RIOT_API_KEY not set")
        return MockRiotAPIClient()

    # TODO iteración futura: implementar HttpRiotAPIClient en http_client.py y
    # delegar aquí cuando la feature de vinculación Riot + verificación API entre en scope.
    raise NotImplementedError(
        "HttpRiotAPIClient is deferred until the Riot-linking feature. "
        "Unset RIOT_API_KEY to use MockRiotAPIClient."
    )
