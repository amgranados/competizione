"""HttpRiotAPIClient — production implementation backed by httpx.

Vinculación de cuenta (resolve_puuid):
  GET https://{continent}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/
      {game_name}/{tag_line}
  continent ∈ {europe, asia, americas}. Éxito = HTTP 200.

Champion mastery vive en hosts de plataforma (EUW1, NA1, KR, ...):
  GET https://{platform}.api.riotgames.com/lol/champion-mastery/v4/
      champion-masteries/by-puuid/{puuid}

La autenticación se envía en la cabecera `X-Riot-Token` (formato canónico de
Riot). El query-param `api_key=...` también está documentado pero Riot lo
rechaza con frecuencia para dev keys, devolviendo 401 "Unknown apikey".
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import quote

import httpx

from app.services.riot_api.client import (
    ChampionMastery,
    LobbyEvent,
    MatchSummary,
    RankedEntry,
    RankedStats,
    RiotIdentityError,
    RiotUnavailableError,
    SummonerProfile,
)

logger = logging.getLogger(__name__)

_VALID_REGIONS = frozenset({"europe", "asia", "americas"})
_DEFAULT_TIMEOUT = httpx.Timeout(5.0, connect=3.0)

# Las Tournament APIs (v5 y su stub) se sirven SIEMPRE desde el host AMERICAS,
# independientemente de la región del provider.
_TOURNAMENT_HOST = "https://americas.api.riotgames.com"
_STUB_BASE = f"{_TOURNAMENT_HOST}/lol/tournament-stub/v5"


class HttpRiotAPIClient:
    """Async Riot API client using httpx.

    Methods match the RiotAPIClient Protocol. Each method maps Riot HTTP
    failures to two domain exceptions:
    - 4xx (identity/auth) → RiotIdentityError
    - 5xx + timeout/connect → RiotUnavailableError
    """

    def __init__(self, api_key: str, timeout: httpx.Timeout | None = None):
        self._api_key = api_key
        self._timeout = timeout or _DEFAULT_TIMEOUT

    # 002 stubs (kept for interface compatibility; not consumed in 003)
    def validate_riot_id(self, game_name: str, tag_line: str) -> bool:
        raise NotImplementedError("validate_riot_id is unused in 003 (verification deferred)")

    def get_match_by_tournament_code(self, tournament_code: str):
        raise NotImplementedError("get_match_by_tournament_code is deferred")

    # 003 helpers --------------------------------------------------------

    def _regional_host(self, region: str) -> str:
        normalized = region.lower()
        if normalized not in _VALID_REGIONS:
            raise RiotIdentityError(f"Unsupported region: {region}")
        return f"https://{normalized}.api.riotgames.com"

    def _platform_host(self, platform: str) -> str:
        return f"https://{platform.lower()}.api.riotgames.com"

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=self._timeout,
            headers={"X-Riot-Token": self._api_key},
        )

    async def _get(self, client: httpx.AsyncClient, url: str) -> httpx.Response:
        """Send GET; auth header is already attached by `_client()`.

        4xx → RiotIdentityError, 5xx / network → RiotUnavailableError.
        """
        try:
            response = await client.get(url)
        except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as exc:
            logger.warning("Riot network error for %s: %s", url, exc)
            raise RiotUnavailableError(str(exc)) from exc

        if 400 <= response.status_code < 500:
            logger.warning("Riot 4xx %s for %s", response.status_code, url)
            raise RiotIdentityError(f"Riot 4xx for {url}: {response.status_code}")
        if 500 <= response.status_code < 600:
            logger.warning("Riot 5xx %s for %s", response.status_code, url)
            raise RiotUnavailableError(f"Riot 5xx for {url}: {response.status_code}")
        return response

    async def _post(self, client: httpx.AsyncClient, url: str, payload: dict) -> httpx.Response:
        """Send POST with JSON body; same error mapping as `_get`."""
        try:
            response = await client.post(url, json=payload)
        except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as exc:
            logger.warning("Riot network error for %s: %s", url, exc)
            raise RiotUnavailableError(str(exc)) from exc

        if 400 <= response.status_code < 500:
            logger.warning("Riot 4xx %s for %s: %s", response.status_code, url, response.text)
            raise RiotIdentityError(f"Riot 4xx for {url}: {response.status_code}")
        if 500 <= response.status_code < 600:
            logger.warning("Riot 5xx %s for %s", response.status_code, url)
            raise RiotUnavailableError(f"Riot 5xx for {url}: {response.status_code}")
        return response

    # 003 methods --------------------------------------------------------

    async def resolve_puuid(self, game_name: str, tag_line: str, region: str) -> str:
        """Resolve a Riot ID to its PUUID via account/v1.

        `region` is the continent (europe/asia/americas). On 200 we return
        the PUUID from the body; if it's missing (extremely rare) we fall
        back to a deterministic synthetic id to keep the model integrity.
        """
        # L-02: escapar game_name/tag_line para que no rompan/alteren la ruta
        # (p. ej. un "/" o caracteres reservados en el Riot ID).
        url = (
            f"{self._regional_host(region)}/riot/account/v1/accounts/by-riot-id/"
            f"{quote(game_name, safe='')}/{quote(tag_line, safe='')}"
        )
        async with self._client() as client:
            response = await self._get(client, url)
        try:
            puuid = response.json().get("puuid")
        except ValueError:
            puuid = None
        if not puuid:
            puuid = f"riot:{region}:{game_name}#{tag_line}"
        return puuid

    async def get_summoner_profile(self, puuid: str, region: str) -> SummonerProfile:
        url = (
            f"{self._platform_host(region)}/lol/summoner/v4/summoners/by-puuid/{puuid}"
        )
        async with self._client() as client:
            response = await self._get(client, url)
        data = response.json()
        return SummonerProfile(
            summoner_level=int(data.get("summonerLevel", 0)),
            region=region,
            profile_icon_id=int(data.get("profileIconId", 0)),
        )

    async def get_ranked_stats(self, puuid: str, region: str) -> RankedStats:
        url = (
            f"{self._platform_host(region)}/lol/league/v4/entries/by-puuid/{puuid}"
        )
        async with self._client() as client:
            response = await self._get(client, url)
        entries = response.json()
        solo = next((e for e in entries if e.get("queueType") == "RANKED_SOLO_5x5"), None)
        flex = next((e for e in entries if e.get("queueType") == "RANKED_FLEX_SR"), None)
        return RankedStats(
            solo_duo=_to_ranked_entry(solo),
            flex=_to_ranked_entry(flex),
        )

    async def get_champion_mastery(
        self, puuid: str, region: str, limit: int | None = None
    ) -> list[ChampionMastery]:
        """Fetch all champion masteries for `puuid` from the platform host.

        `region` is the platform code (EUW1, NA1, KR, ...). The endpoint
        returns every champion the user has played; if `limit` is given the
        list is truncated client-side after sorting by championPoints desc.
        """
        url = (
            f"{self._platform_host(region)}/lol/champion-mastery/v4/"
            f"champion-masteries/by-puuid/{puuid}"
        )
        async with self._client() as client:
            response = await self._get(client, url)
        items = [
            ChampionMastery(
                champion_id=int(item["championId"]),
                champion_level=int(item.get("championLevel", 0)),
                champion_points=int(item.get("championPoints", 0)),
            )
            for item in response.json()
        ]
        items.sort(key=lambda m: m.champion_points, reverse=True)
        if limit is not None:
            items = items[:limit]
        return items

    async def get_recent_matches(
        self, puuid: str, region: str, limit: int = 5
    ) -> list[MatchSummary]:
        regional = self._regional_host(region)
        ids_url = f"{regional}/lol/match/v5/matches/by-puuid/{puuid}/ids?count={limit}"
        async with self._client() as client:
            response = await self._get(client, ids_url)
            match_ids = response.json()
            summaries: list[MatchSummary] = []
            for match_id in match_ids:
                detail = await self._get(
                    client,
                    f"{regional}/lol/match/v5/matches/{match_id}",
                )
                summaries.append(_match_summary(detail.json(), puuid))
        return summaries


    # Tournament-Stub-V5 ---------------------------------------------------

    async def create_tournament_provider(self, region: str, callback_url: str) -> int:
        """POST /providers — registra la app como proveedor de torneos.

        `region` es la plataforma del torneo (EUW, NA, KR…); `callback_url`
        (https) es donde Riot enviaría los resultados de cada partida al
        terminar. Devuelve el providerId que exigen el resto de endpoints.
        """
        async with self._client() as client:
            response = await self._post(
                client,
                f"{_STUB_BASE}/providers",
                {"region": region.upper(), "url": callback_url},
            )
        return int(response.json())

    async def create_tournament(self, provider_id: int, name: str) -> int:
        """POST /tournaments — crea el contenedor lógico del torneo en Riot."""
        async with self._client() as client:
            response = await self._post(
                client,
                f"{_STUB_BASE}/tournaments",
                {"providerId": provider_id, "name": name},
            )
        return int(response.json())

    async def create_tournament_codes(
        self,
        tournament_id: int,
        count: int,
        *,
        team_size: int = 1,
        allowed_puuids: list[str] | None = None,
        metadata: str | None = None,
    ) -> list[str]:
        """POST /codes — genera códigos de partida para un torneo.

        Cada código se introduce en el cliente de LoL para crear la lobby de
        esa partida. `allowed_puuids` restringe quién puede entrar;
        `metadata` viaja de vuelta en el callback de resultados (usamos el id
        interno de la Match para correlacionar).
        """
        payload: dict = {
            "teamSize": team_size,
            "mapType": "SUMMONERS_RIFT",
            "pickType": "TOURNAMENT_DRAFT",
            "spectatorType": "ALL",
            "enoughPlayers": False,
        }
        if allowed_puuids:
            payload["allowedParticipants"] = allowed_puuids
        if metadata:
            payload["metadata"] = metadata
        url = f"{_STUB_BASE}/codes?tournamentId={tournament_id}&count={count}"
        async with self._client() as client:
            response = await self._post(client, url, payload)
        return [str(code) for code in response.json()]

    async def get_lobby_events(self, tournament_code: str) -> list[LobbyEvent]:
        """GET /lobby-events/by-code/{code} — eventos de la lobby del código."""
        url = f"{_STUB_BASE}/lobby-events/by-code/{quote(tournament_code, safe='')}"
        async with self._client() as client:
            response = await self._get(client, url)
        events = response.json().get("eventList", []) or []
        return [
            LobbyEvent(
                timestamp=str(e.get("timestamp", "")),
                event_type=str(e.get("eventType", "")),
                puuid=e.get("puuid"),
            )
            for e in events
        ]


def _to_ranked_entry(raw: dict | None) -> RankedEntry | None:
    if raw is None:
        return None
    return RankedEntry(
        queue_type=raw["queueType"],
        tier=str(raw.get("tier", "")),
        rank=str(raw.get("rank", "")),
        league_points=int(raw.get("leaguePoints", 0)),
        wins=int(raw.get("wins", 0)),
        losses=int(raw.get("losses", 0)),
    )


def _match_summary(detail: dict, puuid: str) -> MatchSummary:
    info = detail.get("info", {})
    me = next((p for p in info.get("participants", []) if p.get("puuid") == puuid), {})
    metadata = detail.get("metadata", {})
    played_at = datetime.fromtimestamp(int(info.get("gameStartTimestamp", 0)) / 1000, tz=timezone.utc)
    return MatchSummary(
        match_id=str(metadata.get("matchId", "")),
        played_at=played_at,
        duration_seconds=int(info.get("gameDuration", 0)),
        champion_id=int(me.get("championId", 0)),
        kills=int(me.get("kills", 0)),
        deaths=int(me.get("deaths", 0)),
        assists=int(me.get("assists", 0)),
        win=bool(me.get("win", False)),
        queue=str(info.get("gameMode", "")),
    )
