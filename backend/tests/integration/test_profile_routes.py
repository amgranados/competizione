"""Integration tests for /api/profile routes (003-edit-profile)."""
from __future__ import annotations

import pytest

from tests.helpers import register_user, switch_user


@pytest.mark.asyncio
async def test_get_profile_requires_authentication(async_client):
    """T009: GET /api/profile without cookies returns 401."""
    async_client.cookies.clear()
    response = await async_client.get("/api/profile")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_profile_returns_basic_data_for_user_without_lol(async_client):
    """T010: authenticated user without RiotAccount → 200 with basic payload."""
    user = await register_user(async_client, "alice@example.com", "alice")

    response = await async_client.get("/api/profile")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == user["id"]
    assert body["nickname"] == "alice"
    assert body["email"] == "alice@example.com"
    assert body["avatar_url"] is None
    assert body["linked_games"] == []
    assert body["lol_stats"] is None


# ===== US1 — PATCH /nickname ============================================

@pytest.mark.asyncio
async def test_patch_nickname_returns_200_with_updated_profile(async_client):
    await register_user(async_client, "alice@example.com", "alice")

    response = await async_client.patch("/api/profile/nickname", json={"nickname": "alicenew"})

    assert response.status_code == 200, response.text
    assert response.json()["nickname"] == "alicenew"


@pytest.mark.asyncio
async def test_patch_nickname_returns_409_when_taken(async_client):
    bob = await register_user(async_client, "bob@example.com", "bob")
    alice = await register_user(async_client, "alice@example.com", "alice")
    switch_user(async_client, alice)

    response = await async_client.patch("/api/profile/nickname", json={"nickname": "bob"})

    assert response.status_code == 409
    # alice's nickname must remain unchanged
    me = await async_client.get("/api/profile")
    assert me.json()["nickname"] == "alice"


@pytest.mark.asyncio
async def test_patch_nickname_returns_422_on_invalid_format(async_client):
    await register_user(async_client, "alice@example.com", "alice")

    response = await async_client.patch("/api/profile/nickname", json={"nickname": ""})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_patch_nickname_idempotent_when_same_as_current(async_client):
    await register_user(async_client, "alice@example.com", "alice")

    response = await async_client.patch("/api/profile/nickname", json={"nickname": "alice"})
    assert response.status_code == 200
    assert response.json()["nickname"] == "alice"


# ===== US1 — PATCH /password ============================================

@pytest.mark.asyncio
async def test_patch_password_returns_204_and_rotates_cookies(async_client):
    await register_user(async_client, "alice@example.com", "alice", password="hunter2-abc")

    old_access = async_client.cookies.get("access_token")
    response = await async_client.patch(
        "/api/profile/password",
        json={"current_password": "hunter2-abc", "new_password": "NewPassword99"},
    )

    assert response.status_code == 204
    set_cookies = response.headers.get_list("set-cookie")
    assert any("access_token=" in h for h in set_cookies)
    assert any("refresh_token=" in h for h in set_cookies)
    # New cookie should differ from the old one (rotated)
    new_access_lines = [h for h in set_cookies if h.startswith("access_token=")]
    assert new_access_lines, "no access_token Set-Cookie emitted"
    assert old_access not in new_access_lines[0]


@pytest.mark.asyncio
async def test_patch_password_returns_400_on_wrong_current_password(async_client):
    await register_user(async_client, "alice@example.com", "alice", password="hunter2-abc")

    response = await async_client.patch(
        "/api/profile/password",
        json={"current_password": "wrong", "new_password": "NewPassword99"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_patch_password_returns_422_on_short_new_password(async_client):
    await register_user(async_client, "alice@example.com", "alice", password="hunter2-abc")

    response = await async_client.patch(
        "/api/profile/password",
        json={"current_password": "hunter2-abc", "new_password": "short"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_patch_password_invalidates_other_sessions_globally(async_client):
    """A second login of the same user becomes invalid after the first changes pass.

    JWT `iat` has 1-second resolution; we sleep briefly between login and
    password change so the second session is provably "before" the bump.
    """
    import asyncio

    await register_user(async_client, "alice@example.com", "alice", password="hunter2-abc")
    primary_cookies = dict(async_client.cookies)

    # Open a second session by re-logging in (different jti, new refresh token)
    async_client.cookies.clear()
    login_resp = await async_client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "hunter2-abc"},
    )
    assert login_resp.status_code == 200
    second_cookies = {}
    for header in login_resp.headers.get_list("set-cookie"):
        name_value = header.split(";", 1)[0]
        if "=" in name_value:
            name, value = name_value.split("=", 1)
            second_cookies[name.strip()] = value.strip()

    await asyncio.sleep(1.1)

    # Restore primary session and change password
    async_client.cookies.clear()
    for k, v in primary_cookies.items():
        async_client.cookies.set(k, v)
    response = await async_client.patch(
        "/api/profile/password",
        json={"current_password": "hunter2-abc", "new_password": "NewPassword99"},
    )
    assert response.status_code == 204

    # Now the second session's refresh token must be rejected
    async_client.cookies.clear()
    for k, v in second_cookies.items():
        async_client.cookies.set(k, v)
    refresh_resp = await async_client.post("/auth/refresh")
    assert refresh_resp.status_code == 401


# ===== US1 — PATCH /avatar ==============================================

@pytest.mark.asyncio
async def test_patch_avatar_returns_200_with_updated_url(async_client):
    await register_user(async_client, "alice@example.com", "alice")

    response = await async_client.patch(
        "/api/profile/avatar",
        json={"avatar_url": "https://cdn.example/me.png"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["avatar_url"].startswith("https://cdn.example/me.png")


@pytest.mark.asyncio
async def test_patch_avatar_returns_422_on_invalid_url(async_client):
    await register_user(async_client, "alice@example.com", "alice")

    response = await async_client.patch("/api/profile/avatar", json={"avatar_url": "not-a-url"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_patch_avatar_accepts_null_to_reset_to_default(async_client):
    await register_user(async_client, "alice@example.com", "alice")
    await async_client.patch("/api/profile/avatar", json={"avatar_url": "https://cdn.example/old.png"})

    response = await async_client.patch("/api/profile/avatar", json={"avatar_url": None})

    assert response.status_code == 200
    assert response.json()["avatar_url"] is None


# ===== US2 — link / unlink LoL ==========================================

import pytest_asyncio  # noqa: E402

from app.api.routes.profile import get_riot_client  # noqa: E402
from app.main import app  # noqa: E402
from app.models.participant import Participant as ParticipantModel  # noqa: E402
from app.models.tournament import Tournament as TournamentModel  # noqa: E402
from app.services.riot_api.client import (  # noqa: E402
    ChampionMastery,
    MatchSummary,
    RankedEntry,
    RankedStats,
    SummonerProfile,
)
from app.services.riot_api.mock_client import MockRiotAPIClient  # noqa: E402


@pytest_asyncio.fixture
async def riot_mock():
    """Mock Riot client injected via dependency override for US2 tests."""
    client = MockRiotAPIClient()
    app.dependency_overrides[get_riot_client] = lambda: client
    yield client
    app.dependency_overrides.pop(get_riot_client, None)


@pytest.mark.asyncio
async def test_post_link_lol_returns_201_and_persists(async_client, riot_mock):
    await register_user(async_client, "alice@example.com", "alice")
    riot_mock.configured_puuids[("Faker", "KR1")] = "PUUID-FAKER"

    response = await async_client.post(
        "/api/profile/link/lol",
        json={"game_name": "Faker", "tag_line": "KR1", "region": "asia"},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["game"] == "lol"
    assert body["region"] == "asia"


@pytest.mark.asyncio
async def test_post_link_lol_returns_400_for_invalid_riot_id(async_client, riot_mock):
    await register_user(async_client, "alice@example.com", "alice")
    # No puuid configured for ("Bad","X") → mock raises RiotIdentityError

    response = await async_client.post(
        "/api/profile/link/lol",
        json={"game_name": "Bad", "tag_line": "X", "region": "europe"},
    )

    assert response.status_code == 400
    assert "Verifica los datos" in response.json()["detail"]


@pytest.mark.asyncio
async def test_post_link_lol_returns_422_for_unknown_region(async_client, riot_mock):
    await register_user(async_client, "alice@example.com", "alice")

    response = await async_client.post(
        "/api/profile/link/lol",
        json={"game_name": "X", "tag_line": "Y", "region": "ZZZ"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_link_lol_returns_503_when_riot_unavailable(async_client, riot_mock):
    await register_user(async_client, "alice@example.com", "alice")
    riot_mock.unavailable_methods["resolve_puuid"] = {("X", "Y")}

    response = await async_client.post(
        "/api/profile/link/lol",
        json={"game_name": "X", "tag_line": "Y", "region": "europe"},
    )

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_post_link_lol_returns_409_when_already_linked(async_client, riot_mock):
    await register_user(async_client, "alice@example.com", "alice")
    riot_mock.configured_puuids[("Faker", "KR1")] = "PUUID-FAKER"
    riot_mock.configured_puuids[("Other", "TAG")] = "ANOTHER-PUUID"

    first = await async_client.post(
        "/api/profile/link/lol",
        json={"game_name": "Faker", "tag_line": "KR1", "region": "asia"},
    )
    assert first.status_code == 201

    second = await async_client.post(
        "/api/profile/link/lol",
        json={"game_name": "Other", "tag_line": "TAG", "region": "asia"},
    )
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_delete_link_lol_returns_204_when_no_active_tournament(async_client, riot_mock):
    await register_user(async_client, "alice@example.com", "alice")
    riot_mock.configured_puuids[("Faker", "KR1")] = "PUUID-FAKER"
    await async_client.post(
        "/api/profile/link/lol",
        json={"game_name": "Faker", "tag_line": "KR1", "region": "asia"},
    )

    response = await async_client.delete("/api/profile/link/lol")

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_link_lol_returns_404_when_not_linked(async_client, riot_mock):
    await register_user(async_client, "alice@example.com", "alice")

    response = await async_client.delete("/api/profile/link/lol")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_profile_includes_lol_stats_in_payload(async_client, riot_mock):
    user = await register_user(async_client, "alice@example.com", "alice")
    riot_mock.configured_puuids[("Faker", "KR1")] = "PUUID-FAKER"
    riot_mock.configured_summoner["PUUID-FAKER"] = SummonerProfile(120, "asia")
    riot_mock.configured_ranked["PUUID-FAKER"] = RankedStats(
        solo_duo=RankedEntry("RANKED_SOLO_5x5", "GOLD", "II", 50, 30, 20), flex=None
    )
    riot_mock.configured_mastery["PUUID-FAKER"] = [ChampionMastery(7, 7, 100_000)]
    from datetime import datetime, timezone

    riot_mock.configured_matches["PUUID-FAKER"] = [
        MatchSummary("M1", datetime(2026, 4, 25, tzinfo=timezone.utc), 1500, 7, 5, 3, 9, True, "RANKED_SOLO")
    ]
    await async_client.post(
        "/api/profile/link/lol",
        json={"game_name": "Faker", "tag_line": "KR1", "region": "asia"},
    )

    response = await async_client.get("/api/profile")

    assert response.status_code == 200
    body = response.json()
    assert body["linked_games"][0]["game"] == "lol"
    stats = body["lol_stats"]
    assert stats is not None
    assert stats["summoner"]["unavailable"] is False
    assert stats["summoner"]["data"]["summoner_level"] == 120
    assert stats["ranked"]["solo_duo"]["tier"] == "GOLD"
    assert stats["mastery"]["data"][0]["champion_id"] == 7
    assert stats["recent_matches"]["data"][0]["match_id"] == "M1"


@pytest.mark.asyncio
async def test_get_profile_partial_riot_failure_marks_unavailable(async_client, riot_mock):
    await register_user(async_client, "alice@example.com", "alice")
    riot_mock.configured_puuids[("Faker", "KR1")] = "PUUID-FAKER"
    riot_mock.configured_summoner["PUUID-FAKER"] = SummonerProfile(120, "asia")
    riot_mock.configured_ranked["PUUID-FAKER"] = RankedStats(solo_duo=None, flex=None)
    riot_mock.configured_mastery["PUUID-FAKER"] = []
    riot_mock.unavailable_methods["get_recent_matches"] = {"PUUID-FAKER"}
    await async_client.post(
        "/api/profile/link/lol",
        json={"game_name": "Faker", "tag_line": "KR1", "region": "asia"},
    )

    response = await async_client.get("/api/profile")

    assert response.status_code == 200
    stats = response.json()["lol_stats"]
    assert stats["summoner"]["unavailable"] is False
    assert stats["recent_matches"]["unavailable"] is True
    assert stats["recent_matches"]["data"] is None


# ===== US3 — DELETE /api/profile/me =====================================

@pytest.mark.asyncio
async def test_delete_me_returns_204_and_clears_cookies_on_success(async_client):
    await register_user(async_client, "alice@example.com", "alice")

    response = await async_client.request(
        "DELETE", "/api/profile/me", json={"confirmation": "alice"}
    )

    assert response.status_code == 204
    set_cookies = response.headers.get_list("set-cookie")
    assert any("access_token=;" in h or "access_token=" in h and "max-age=0" in h.lower() for h in set_cookies)


@pytest.mark.asyncio
async def test_delete_me_returns_400_when_confirmation_wrong(async_client):
    await register_user(async_client, "alice@example.com", "alice")

    response = await async_client.request(
        "DELETE", "/api/profile/me", json={"confirmation": "Alice"}
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_delete_me_returns_409_when_active_tournament(async_client, db_session):
    user = await register_user(async_client, "alice@example.com", "alice")

    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    import uuid as uuid_mod

    factory = async_sessionmaker(db_session.bind, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        user_uuid = uuid_mod.UUID(user["id"])
        tournament = TournamentModel(
            name="t", format="round_robin", state="open", organizer_id=user_uuid
        )
        session.add(tournament)
        await session.commit()
        session.add(ParticipantModel(tournament_id=tournament.id, user_id=user_uuid))
        await session.commit()

    response = await async_client.request(
        "DELETE", "/api/profile/me", json={"confirmation": "alice"}
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_after_delete_account_is_rejected(async_client):
    await register_user(async_client, "alice@example.com", "alice", password="hunter2-abc")

    response = await async_client.request(
        "DELETE", "/api/profile/me", json={"confirmation": "alice"}
    )
    assert response.status_code == 204

    async_client.cookies.clear()
    login = await async_client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "hunter2-abc"},
    )
    assert login.status_code == 401


@pytest.mark.asyncio
async def test_delete_link_lol_returns_409_when_active_tournament(async_client, riot_mock, db_session):
    """Direct DB seeding to create an active-tournament participation."""
    user = await register_user(async_client, "alice@example.com", "alice")
    riot_mock.configured_puuids[("Faker", "KR1")] = "PUUID-FAKER"
    await async_client.post(
        "/api/profile/link/lol",
        json={"game_name": "Faker", "tag_line": "KR1", "region": "asia"},
    )

    # Inject an active-state tournament + participant directly via the test session.
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

    factory = async_sessionmaker(db_session.bind, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        import uuid as uuid_mod

        user_uuid = uuid_mod.UUID(user["id"])
        tournament = TournamentModel(
            name="t", format="round_robin", state="open", organizer_id=user_uuid
        )
        session.add(tournament)
        await session.commit()
        session.add(ParticipantModel(tournament_id=tournament.id, user_id=user_uuid))
        await session.commit()

    response = await async_client.delete("/api/profile/link/lol")

    assert response.status_code == 409
