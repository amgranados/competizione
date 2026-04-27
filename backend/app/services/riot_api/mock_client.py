"""MockRiotAPIClient — fixture-driven implementation for tests and local dev.

Used automatically by get_riot_api_client() when RIOT_API_KEY is not set.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.services.riot_api.client import (
    ChampionMastery,
    MatchResult,
    MatchSummary,
    RankedStats,
    RiotIdentityError,
    RiotUnavailableError,
    SummonerProfile,
)


@dataclass
class MockRiotAPIClient:
    """Fixture-friendly client. Tests populate the configured_* maps to
    drive deterministic responses. Unconfigured keys raise the appropriate
    domain exception so the calling code can be exercised end-to-end.
    """

    # 002 (verbatim)
    configured_match_results: dict[str, MatchResult] = field(default_factory=dict)
    configured_riot_ids: set[tuple[str, str]] = field(default_factory=set)

    # 003
    configured_puuids: dict[tuple[str, str], str] = field(default_factory=dict)
    configured_summoner: dict[str, SummonerProfile] = field(default_factory=dict)
    configured_ranked: dict[str, RankedStats] = field(default_factory=dict)
    configured_mastery: dict[str, list[ChampionMastery]] = field(default_factory=dict)
    configured_matches: dict[str, list[MatchSummary]] = field(default_factory=dict)
    # Set of puuids for which a given method should raise RiotUnavailableError
    unavailable_for: set[str] = field(default_factory=set)
    unavailable_methods: dict[str, set[str]] = field(default_factory=dict)

    # ----- 002 -----

    def validate_riot_id(self, game_name: str, tag_line: str) -> bool:
        return (game_name, tag_line) in self.configured_riot_ids

    def get_match_by_tournament_code(self, tournament_code: str) -> MatchResult | None:
        return self.configured_match_results.get(tournament_code)

    # ----- 003 helpers -----

    def _maybe_unavailable(self, method: str, puuid: str) -> None:
        if puuid in self.unavailable_for:
            raise RiotUnavailableError(f"{method} unavailable for {puuid}")
        if puuid in self.unavailable_methods.get(method, set()):
            raise RiotUnavailableError(f"{method} unavailable for {puuid}")

    # ----- 003 methods -----

    async def resolve_puuid(self, game_name: str, tag_line: str, region: str) -> str:
        if (game_name, tag_line) in self.unavailable_methods.get("resolve_puuid", set()):
            raise RiotUnavailableError("Riot unavailable")
        try:
            return self.configured_puuids[(game_name, tag_line)]
        except KeyError as exc:
            raise RiotIdentityError(f"Unknown Riot ID {game_name}#{tag_line}") from exc

    async def get_summoner_profile(self, puuid: str, region: str) -> SummonerProfile:
        self._maybe_unavailable("get_summoner_profile", puuid)
        try:
            return self.configured_summoner[puuid]
        except KeyError as exc:
            raise RiotUnavailableError(f"summoner profile not seeded for {puuid}") from exc

    async def get_ranked_stats(self, puuid: str, region: str) -> RankedStats:
        self._maybe_unavailable("get_ranked_stats", puuid)
        try:
            return self.configured_ranked[puuid]
        except KeyError as exc:
            raise RiotUnavailableError(f"ranked stats not seeded for {puuid}") from exc

    async def get_champion_mastery(
        self, puuid: str, region: str, limit: int = 5
    ) -> list[ChampionMastery]:
        self._maybe_unavailable("get_champion_mastery", puuid)
        try:
            return self.configured_mastery[puuid][:limit]
        except KeyError as exc:
            raise RiotUnavailableError(f"mastery not seeded for {puuid}") from exc

    async def get_recent_matches(
        self, puuid: str, region: str, limit: int = 5
    ) -> list[MatchSummary]:
        self._maybe_unavailable("get_recent_matches", puuid)
        try:
            return self.configured_matches[puuid][:limit]
        except KeyError as exc:
            raise RiotUnavailableError(f"matches not seeded for {puuid}") from exc
