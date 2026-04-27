"""Tests for the Riot API client (Protocol + Mock + factory).

Covers T004 and T005: the Mock implements the Protocol and returns configured
data; the factory returns MockRiotAPIClient when RIOT_API_KEY is unset and emits
an explicit INFO log about it.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import pytest

from app.services.riot_api.client import (
    MatchResult,
    ParticipantInfo,
    RiotAPIClient,
    get_riot_api_client,
)
from app.services.riot_api.mock_client import MockRiotAPIClient


def test_mock_client_returns_configured_match_result():
    client = MockRiotAPIClient()
    fixture = MatchResult(
        participants=[
            ParticipantInfo(puuid="p1", team_id=100),
            ParticipantInfo(puuid="p2", team_id=200),
        ],
        duration_seconds=600,
        game_mode="CLASSIC",
        start_timestamp=datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc),
    )
    client.configured_match_results["TC-123"] = fixture

    assert client.get_match_by_tournament_code("TC-123") == fixture
    assert client.get_match_by_tournament_code("TC-missing") is None


def test_mock_client_validate_riot_id_uses_configured_set():
    client = MockRiotAPIClient()
    client.configured_riot_ids.add(("Faker", "KR1"))

    assert client.validate_riot_id("Faker", "KR1") is True
    assert client.validate_riot_id("Nobody", "EUW") is False


def test_mock_client_satisfies_protocol():
    client: RiotAPIClient = MockRiotAPIClient()
    assert hasattr(client, "validate_riot_id")
    assert hasattr(client, "get_match_by_tournament_code")


def test_factory_returns_mock_when_api_key_missing_and_logs(caplog):
    class FakeSettings:
        RIOT_API_KEY: str | None = None

    with caplog.at_level(logging.INFO, logger="app.services.riot_api.client"):
        client = get_riot_api_client(FakeSettings())

    assert isinstance(client, MockRiotAPIClient)
    messages = [rec.message for rec in caplog.records]
    assert any("Using MockRiotAPIClient: RIOT_API_KEY not set" in m for m in messages)


def test_factory_returns_http_client_when_api_key_present():
    """T067: 003 wires HttpRiotAPIClient when the key is set."""
    from app.services.riot_api.http_client import HttpRiotAPIClient

    class FakeSettings:
        RIOT_API_KEY: str | None = "fake-key"

    client = get_riot_api_client(FakeSettings())
    assert isinstance(client, HttpRiotAPIClient)


# ===== 003 — Mock client tests ==========================================

@pytest.mark.asyncio
async def test_mock_get_summoner_profile_returns_seeded_data():
    from app.services.riot_api.client import SummonerProfile

    client = MockRiotAPIClient()
    client.configured_summoner["P1"] = SummonerProfile(summoner_level=120, region="EUW1")

    result = await client.get_summoner_profile("P1", "EUW1")
    assert result == SummonerProfile(summoner_level=120, region="EUW1")


@pytest.mark.asyncio
async def test_mock_get_ranked_stats_returns_seeded_data():
    from app.services.riot_api.client import RankedEntry, RankedStats

    client = MockRiotAPIClient()
    solo = RankedEntry("RANKED_SOLO_5x5", "GOLD", "II", 50, 30, 20)
    client.configured_ranked["P1"] = RankedStats(solo_duo=solo, flex=None)

    result = await client.get_ranked_stats("P1", "EUW1")
    assert result.solo_duo == solo
    assert result.flex is None


@pytest.mark.asyncio
async def test_mock_get_champion_mastery_respects_limit():
    from app.services.riot_api.client import ChampionMastery

    client = MockRiotAPIClient()
    masteries = [ChampionMastery(i, 7, 100_000 - i) for i in range(10)]
    client.configured_mastery["P1"] = masteries

    result = await client.get_champion_mastery("P1", "EUW1", limit=3)
    assert len(result) == 3
    assert result == masteries[:3]


@pytest.mark.asyncio
async def test_mock_get_recent_matches_respects_limit():
    from app.services.riot_api.client import MatchSummary

    client = MockRiotAPIClient()
    base = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    summaries = [
        MatchSummary(f"M{i}", base, 1500, 1, 5, 3, 2, True, "RANKED_SOLO") for i in range(7)
    ]
    client.configured_matches["P1"] = summaries

    result = await client.get_recent_matches("P1", "EUW1", limit=5)
    assert len(result) == 5
    assert result == summaries[:5]


@pytest.mark.asyncio
async def test_mock_resolve_puuid_returns_seeded_value_or_raises():
    from app.services.riot_api.client import RiotIdentityError

    client = MockRiotAPIClient()
    client.configured_puuids[("Faker", "KR1")] = "PUUID-FAKER"

    assert await client.resolve_puuid("Faker", "KR1", "KR") == "PUUID-FAKER"
    with pytest.raises(RiotIdentityError):
        await client.resolve_puuid("Nobody", "EUW", "EUW1")


# ===== 003 — Http client tests via respx ================================

import respx  # noqa: E402
from httpx import Response  # noqa: E402

from app.services.riot_api.client import RiotIdentityError, RiotUnavailableError  # noqa: E402
from app.services.riot_api.http_client import HttpRiotAPIClient  # noqa: E402


@pytest.mark.asyncio
@respx.mock
async def test_http_resolve_puuid_with_respx_200():
    """Vinculación: el éxito es exclusivamente HTTP 200; api_key va en query."""
    route = respx.get(
        "https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/Faker/KR1",
        params={"api_key": "test-key"},
    ).mock(return_value=Response(200, json={"puuid": "PUUID-FAKER"}))

    client = HttpRiotAPIClient(api_key="test-key")
    result = await client.resolve_puuid("Faker", "KR1", "europe")

    assert result == "PUUID-FAKER"
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_http_resolve_puuid_raises_identity_error_on_4xx():
    respx.get(
        "https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/Bad/X"
    ).mock(return_value=Response(404, json={"status": {"message": "not found"}}))

    client = HttpRiotAPIClient(api_key="test-key")
    with pytest.raises(RiotIdentityError):
        await client.resolve_puuid("Bad", "X", "europe")


@pytest.mark.asyncio
@respx.mock
async def test_http_resolve_puuid_raises_unavailable_on_5xx():
    respx.get(
        "https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/X/X"
    ).mock(return_value=Response(503, json={"status": {"message": "service unavailable"}}))

    client = HttpRiotAPIClient(api_key="test-key")
    with pytest.raises(RiotUnavailableError):
        await client.resolve_puuid("X", "X", "americas")


@pytest.mark.asyncio
@respx.mock
async def test_http_resolve_puuid_falls_back_to_synthetic_when_body_lacks_puuid():
    respx.get(
        "https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id/Faker/KR1"
    ).mock(return_value=Response(200, json={}))

    client = HttpRiotAPIClient(api_key="test-key")
    result = await client.resolve_puuid("Faker", "KR1", "asia")

    assert result == "riot:asia:Faker#KR1"


@pytest.mark.asyncio
@respx.mock
async def test_http_get_summoner_profile_with_respx_200():
    respx.get(
        "https://europe.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/P1"
    ).mock(return_value=Response(200, json={"summonerLevel": 120}))

    client = HttpRiotAPIClient(api_key="test-key")
    result = await client.get_summoner_profile("P1", "europe")

    assert result.summoner_level == 120
    assert result.region == "europe"


@pytest.mark.asyncio
@respx.mock
async def test_http_get_ranked_stats_with_respx_200():
    respx.get(
        "https://europe.api.riotgames.com/lol/league/v4/entries/by-puuid/P1"
    ).mock(
        return_value=Response(
            200,
            json=[
                {
                    "queueType": "RANKED_SOLO_5x5",
                    "tier": "GOLD",
                    "rank": "II",
                    "leaguePoints": 50,
                    "wins": 30,
                    "losses": 20,
                },
                {
                    "queueType": "RANKED_FLEX_SR",
                    "tier": "PLATINUM",
                    "rank": "IV",
                    "leaguePoints": 75,
                    "wins": 40,
                    "losses": 25,
                },
            ],
        )
    )

    client = HttpRiotAPIClient(api_key="test-key")
    result = await client.get_ranked_stats("P1", "europe")

    assert result.solo_duo is not None
    assert result.solo_duo.tier == "GOLD"
    assert result.flex is not None
    assert result.flex.tier == "PLATINUM"


@pytest.mark.asyncio
@respx.mock
async def test_http_get_champion_mastery_with_respx_200():
    respx.get(
        "https://europe.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/P1/top",
        params={"count": "5", "api_key": "test-key"},
    ).mock(
        return_value=Response(
            200,
            json=[
                {"championId": 1, "championLevel": 7, "championPoints": 100000},
                {"championId": 2, "championLevel": 6, "championPoints": 80000},
            ],
        )
    )

    client = HttpRiotAPIClient(api_key="test-key")
    result = await client.get_champion_mastery("P1", "europe", limit=5)

    assert len(result) == 2
    assert result[0].champion_id == 1
    assert result[0].champion_level == 7


@pytest.mark.asyncio
@respx.mock
async def test_http_get_recent_matches_with_respx_200_and_2_matches():
    respx.get(
        "https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/P1/ids",
        params={"count": "5", "api_key": "test-key"},
    ).mock(return_value=Response(200, json=["M1", "M2"]))
    respx.get("https://europe.api.riotgames.com/lol/match/v5/matches/M1").mock(
        return_value=Response(
            200,
            json={
                "metadata": {"matchId": "M1"},
                "info": {
                    "gameStartTimestamp": 1714050000000,
                    "gameDuration": 1500,
                    "gameMode": "CLASSIC",
                    "participants": [
                        {"puuid": "P1", "championId": 7, "kills": 5, "deaths": 3, "assists": 9, "win": True},
                    ],
                },
            },
        )
    )
    respx.get("https://europe.api.riotgames.com/lol/match/v5/matches/M2").mock(
        return_value=Response(
            200,
            json={
                "metadata": {"matchId": "M2"},
                "info": {
                    "gameStartTimestamp": 1714053600000,
                    "gameDuration": 1800,
                    "gameMode": "ARAM",
                    "participants": [
                        {"puuid": "P1", "championId": 8, "kills": 2, "deaths": 6, "assists": 4, "win": False},
                    ],
                },
            },
        )
    )

    client = HttpRiotAPIClient(api_key="test-key")
    result = await client.get_recent_matches("P1", "europe", limit=5)

    assert len(result) == 2
    assert result[0].match_id == "M1"
    assert result[0].champion_id == 7
    assert result[0].win is True
    assert result[1].match_id == "M2"
    assert result[1].win is False


@pytest.mark.asyncio
@respx.mock
async def test_http_resolve_puuid_rejects_unsupported_region():
    """Regiones fuera de la whitelist {europe, asia, americas} → identidad inválida."""
    client = HttpRiotAPIClient(api_key="test-key")
    with pytest.raises(RiotIdentityError):
        await client.resolve_puuid("Faker", "KR1", "EUW1")
