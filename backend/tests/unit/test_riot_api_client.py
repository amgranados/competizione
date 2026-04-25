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


def test_factory_would_return_http_client_when_api_key_present(monkeypatch):
    """When RIOT_API_KEY is set, the factory must NOT return the Mock.

    In this iteration HttpRiotAPIClient is deferred; we assert the factory raises
    an explicit NotImplementedError (instead of silently falling back to Mock).
    That guarantees the hidden branch is wired but un-activated.
    """
    class FakeSettings:
        RIOT_API_KEY: str | None = "fake-key"

    with pytest.raises(NotImplementedError, match="HttpRiotAPIClient"):
        get_riot_api_client(FakeSettings())
