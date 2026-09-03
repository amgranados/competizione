"""MockRiotAPIClient — fixture-driven implementation for tests and local dev.

Used automatically by get_riot_api_client() when RIOT_API_KEY is not set.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.services.riot_api.client import (
    ChampionMastery,
    LobbyEvent,
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

    # Tournament-Stub-V5 (mirrors the sandbox: incremental ids, fake codes)
    stub_unavailable: bool = False
    created_providers: list[dict] = field(default_factory=list)
    created_tournaments: list[dict] = field(default_factory=list)
    created_codes: list[dict] = field(default_factory=list)
    configured_lobby_events: dict[str, list[LobbyEvent]] = field(default_factory=dict)

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

    # ----- Tournament-Stub-V5 -----

    def _stub_guard(self) -> None:
        if self.stub_unavailable:
            raise RiotUnavailableError("tournament stub unavailable")

    async def create_tournament_provider(self, region: str, callback_url: str) -> int:
        self._stub_guard()
        provider_id = 100 + len(self.created_providers)
        self.created_providers.append(
            {"id": provider_id, "region": region, "url": callback_url}
        )
        return provider_id

    async def create_tournament(self, provider_id: int, name: str) -> int:
        self._stub_guard()
        tournament_id = 1000 + len(self.created_tournaments)
        self.created_tournaments.append(
            {"id": tournament_id, "provider_id": provider_id, "name": name}
        )
        return tournament_id

    async def create_tournament_codes(
        self,
        tournament_id: int,
        count: int,
        *,
        team_size: int = 1,
        allowed_puuids: list[str] | None = None,
        metadata: str | None = None,
    ) -> list[str]:
        self._stub_guard()
        codes = []
        for _ in range(count):
            code = f"STUB-{tournament_id}-{uuid.uuid4().hex[:10]}"
            self.created_codes.append(
                {
                    "code": code,
                    "tournament_id": tournament_id,
                    "team_size": team_size,
                    "allowed_puuids": allowed_puuids,
                    "metadata": metadata,
                }
            )
            codes.append(code)
        return codes

    async def get_lobby_events(self, tournament_code: str) -> list[LobbyEvent]:
        self._stub_guard()
        return self.configured_lobby_events.get(tournament_code, [])
