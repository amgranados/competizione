"""Unit tests for profile_service (003-edit-profile)."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.core import security
from app.models.token_blacklist import TokenBlacklist
from app.models.user import User
from app.services import profile_service


def _make_user(nickname: str, email: str = None, password: str = "old-password-1") -> User:
    return User(
        email=email or f"{nickname}@example.com",
        nickname=nickname,
        password_hash=security.hash_password(password),
    )


# ----- Nickname ----------------------------------------------------------

@pytest.mark.asyncio
async def test_update_nickname_accepts_unique_value(db_session):
    alice = _make_user("alice")
    bob = _make_user("bob")
    db_session.add_all([alice, bob])
    await db_session.commit()

    await profile_service.update_nickname(db_session, alice.id, "alice2")

    refreshed = await db_session.get(User, alice.id)
    assert refreshed.nickname == "alice2"


@pytest.mark.asyncio
async def test_update_nickname_rejects_when_taken_by_other(db_session):
    alice = _make_user("alice")
    bob = _make_user("bob")
    db_session.add_all([alice, bob])
    await db_session.commit()

    with pytest.raises(profile_service.NicknameAlreadyTaken):
        await profile_service.update_nickname(db_session, alice.id, "bob")

    refreshed = await db_session.get(User, alice.id)
    assert refreshed.nickname == "alice"


@pytest.mark.asyncio
async def test_update_nickname_idempotent_when_same_as_current(db_session):
    alice = _make_user("alice")
    db_session.add(alice)
    await db_session.commit()

    await profile_service.update_nickname(db_session, alice.id, "alice")

    refreshed = await db_session.get(User, alice.id)
    assert refreshed.nickname == "alice"


# ----- Password ----------------------------------------------------------

@pytest.mark.asyncio
async def test_change_password_validates_current_password(db_session):
    alice = _make_user("alice", password="old-password-1")
    db_session.add(alice)
    await db_session.commit()
    original_hash = alice.password_hash

    with pytest.raises(profile_service.InvalidCurrentPassword):
        await profile_service.change_password(
            db_session,
            user_id=alice.id,
            current_session_jti=uuid.uuid4(),
            current_password="wrong",
            new_password="ValidPwd1234",
        )

    refreshed = await db_session.get(User, alice.id)
    assert refreshed.password_hash == original_hash


@pytest.mark.asyncio
async def test_change_password_validates_new_password_minlength(db_session):
    alice = _make_user("alice", password="old-password-1")
    db_session.add(alice)
    await db_session.commit()

    with pytest.raises(profile_service.WeakPasswordError):
        await profile_service.change_password(
            db_session,
            user_id=alice.id,
            current_session_jti=uuid.uuid4(),
            current_password="old-password-1",
            new_password="short",
        )


@pytest.mark.asyncio
async def test_change_password_blacklists_other_sessions(db_session):
    """HD-5: change_password (a) bumps password_changed_at and (b) honors
    active_jtis to belt-and-braces blacklist sessions other than the current one.
    """
    alice = _make_user("alice", password="old-password-1")
    db_session.add(alice)
    await db_session.commit()

    current_jti = uuid.uuid4()
    other_jti_1 = uuid.uuid4()
    other_jti_2 = uuid.uuid4()

    await profile_service.change_password(
        db_session,
        user_id=alice.id,
        current_session_jti=current_jti,
        current_password="old-password-1",
        new_password="NewPassword99",
        active_jtis=[current_jti, other_jti_1, other_jti_2],
    )

    refreshed = await db_session.get(User, alice.id)
    assert refreshed.password_changed_at is not None, "password_changed_at must be set"

    rows = (await db_session.execute(select(TokenBlacklist).where(TokenBlacklist.user_id == alice.id))).scalars().all()
    blacklisted = {row.jti for row in rows}
    assert other_jti_1 in blacklisted
    assert other_jti_2 in blacklisted
    assert current_jti not in blacklisted, "current session must remain valid"


# ----- Avatar -----------------------------------------------------------

@pytest.mark.asyncio
async def test_update_avatar_persists_https_url(db_session):
    alice = _make_user("alice")
    db_session.add(alice)
    await db_session.commit()

    await profile_service.update_avatar(db_session, alice.id, "https://cdn.example/x.png")

    refreshed = await db_session.get(User, alice.id)
    assert refreshed.avatar_url == "https://cdn.example/x.png"


@pytest.mark.asyncio
async def test_update_avatar_accepts_null_to_clear(db_session):
    alice = _make_user("alice")
    alice.avatar_url = "https://cdn.example/old.png"
    db_session.add(alice)
    await db_session.commit()

    await profile_service.update_avatar(db_session, alice.id, None)

    refreshed = await db_session.get(User, alice.id)
    assert refreshed.avatar_url is None


# ===== US2: link_lol / unlink_lol / fetch_lol_stats =====================

import logging

from app.models.participant import Participant
from app.models.riot_account import RiotAccount
from app.models.tournament import Tournament
from app.services.riot_api.mock_client import MockRiotAPIClient


def _make_mock_with_puuid(game_name: str, tag_line: str, puuid: str) -> MockRiotAPIClient:
    client = MockRiotAPIClient()
    client.configured_puuids[(game_name, tag_line)] = puuid
    return client


@pytest.mark.asyncio
async def test_link_lol_persists_puuid_region_and_riot_id(db_session):
    alice = _make_user("alice")
    db_session.add(alice)
    await db_session.commit()

    client = _make_mock_with_puuid("Faker", "KR1", "PUUID-FAKER")

    account = await profile_service.link_lol(
        db_session,
        user_id=alice.id,
        game_name="Faker",
        tag_line="KR1",
        region="KR",
        riot_client=client,
    )

    assert account.puuid == "PUUID-FAKER"
    # region se persiste como la plataforma elegida (no el continente).
    assert account.region == "KR"
    # El Riot ID (game_name/tag_line) ahora SÍ se persiste.
    assert account.game_name == "Faker"
    assert account.tag_line == "KR1"

    columns = {col.name for col in RiotAccount.__table__.columns}
    assert "game_name" in columns and "tag_line" in columns


@pytest.mark.asyncio
async def test_link_lol_does_not_log_credentials(db_session, caplog):
    alice = _make_user("alice")
    db_session.add(alice)
    await db_session.commit()

    client = _make_mock_with_puuid("SecretName", "T0p", "PUUID-X")

    with caplog.at_level(logging.INFO, logger="app.services.profile_service"):
        await profile_service.link_lol(
            db_session,
            user_id=alice.id,
            game_name="SecretName",
            tag_line="T0p",
            region="EUW1",
            riot_client=client,
        )

    for record in caplog.records:
        assert "SecretName" not in record.getMessage()
        assert "T0p" not in record.getMessage()


@pytest.mark.asyncio
async def test_link_lol_returns_generic_error_on_invalid_riot_id(db_session):
    alice = _make_user("alice")
    db_session.add(alice)
    await db_session.commit()

    # Mock with no configured puuid → resolve_puuid raises RiotIdentityError
    client = MockRiotAPIClient()

    with pytest.raises(profile_service.LinkAccountFailed):
        await profile_service.link_lol(
            db_session,
            user_id=alice.id,
            game_name="Bad",
            tag_line="X",
            region="EUW1",
            riot_client=client,
        )


@pytest.mark.asyncio
async def test_link_lol_propagates_unavailable_when_riot_down(db_session):
    alice = _make_user("alice")
    db_session.add(alice)
    await db_session.commit()

    client = MockRiotAPIClient()
    client.unavailable_methods["resolve_puuid"] = {("X", "Y")}

    with pytest.raises(profile_service.RiotUnavailable):
        await profile_service.link_lol(
            db_session,
            user_id=alice.id,
            game_name="X",
            tag_line="Y",
            region="EUW1",
            riot_client=client,
        )


@pytest.mark.asyncio
async def test_link_lol_rejects_when_user_already_has_riot_account(db_session):
    alice = _make_user("alice")
    db_session.add(alice)
    await db_session.commit()
    db_session.add(RiotAccount(user_id=alice.id, puuid="OLD-PUUID", game_name="Alice", tag_line="EUW", region="EUW1"))
    await db_session.commit()

    client = _make_mock_with_puuid("Faker", "KR1", "NEW-PUUID")

    with pytest.raises(profile_service.RiotAlreadyLinked):
        await profile_service.link_lol(
            db_session,
            user_id=alice.id,
            game_name="Faker",
            tag_line="KR1",
            region="asia",
            riot_client=client,
        )


@pytest.mark.asyncio
async def test_link_lol_rejects_duplicate_puuid_across_users(db_engine):
    """INV-7: same PUUID cannot link to two users."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        alice = _make_user("alice")
        bob = _make_user("bob")
        session.add_all([alice, bob])
        await session.commit()
        a_id, b_id = alice.id, bob.id
        session.add(RiotAccount(user_id=a_id, puuid="SHARED-PUUID", game_name="Alice", tag_line="EUW", region="EUW1"))
        await session.commit()

    async with factory() as session:
        client = _make_mock_with_puuid("Bob", "TAG", "SHARED-PUUID")
        with pytest.raises(profile_service.RiotAccountAlreadyClaimed):
            await profile_service.link_lol(
                session,
                user_id=b_id,
                game_name="Bob",
                tag_line="TAG",
                region="EUW1",
                riot_client=client,
            )


@pytest.mark.asyncio
async def test_unlink_lol_succeeds_when_no_active_tournament(db_session):
    alice = _make_user("alice")
    db_session.add(alice)
    await db_session.commit()
    db_session.add(RiotAccount(user_id=alice.id, puuid="P1", game_name="Alice", tag_line="EUW", region="EUW1"))
    await db_session.commit()

    await profile_service.unlink_lol(db_session, alice.id)

    rows = (await db_session.execute(select(RiotAccount).where(RiotAccount.user_id == alice.id))).all()
    assert rows == []


@pytest.mark.asyncio
async def test_unlink_lol_blocked_by_active_tournament(db_session):
    alice = _make_user("alice")
    db_session.add(alice)
    await db_session.commit()
    db_session.add(RiotAccount(user_id=alice.id, puuid="P1", game_name="Alice", tag_line="EUW", region="EUW1"))
    tournament = Tournament(
        name="t", format="round_robin", state="open", organizer_id=alice.id
    )
    db_session.add(tournament)
    await db_session.commit()
    db_session.add(Participant(tournament_id=tournament.id, user_id=alice.id))
    await db_session.commit()

    with pytest.raises(profile_service.UnlinkBlocked):
        await profile_service.unlink_lol(db_session, alice.id)

    rows = (await db_session.execute(select(RiotAccount).where(RiotAccount.user_id == alice.id))).all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_unlink_lol_blocked_by_in_progress_tournament(db_session):
    """M-02: el estado en curso real es 'active' (fijado por start_tournament).
    El guard debe bloquear la desvinculación también en ese estado."""
    alice = _make_user("alice")
    db_session.add(alice)
    await db_session.commit()
    db_session.add(RiotAccount(user_id=alice.id, puuid="P1", game_name="Alice", tag_line="EUW", region="EUW1"))
    tournament = Tournament(
        name="t", format="round_robin", state="active", organizer_id=alice.id
    )
    db_session.add(tournament)
    await db_session.commit()
    db_session.add(Participant(tournament_id=tournament.id, user_id=alice.id))
    await db_session.commit()

    with pytest.raises(profile_service.UnlinkBlocked):
        await profile_service.unlink_lol(db_session, alice.id)

    rows = (await db_session.execute(select(RiotAccount).where(RiotAccount.user_id == alice.id))).all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_unlink_lol_allowed_when_only_finished_tournaments(db_session):
    alice = _make_user("alice")
    db_session.add(alice)
    await db_session.commit()
    db_session.add(RiotAccount(user_id=alice.id, puuid="P1", game_name="Alice", tag_line="EUW", region="EUW1"))
    tournament = Tournament(
        name="t", format="round_robin", state="finished", organizer_id=alice.id
    )
    db_session.add(tournament)
    await db_session.commit()
    db_session.add(Participant(tournament_id=tournament.id, user_id=alice.id))
    await db_session.commit()

    await profile_service.unlink_lol(db_session, alice.id)

    rows = (await db_session.execute(select(RiotAccount).where(RiotAccount.user_id == alice.id))).all()
    assert rows == []


@pytest.mark.asyncio
async def test_unlink_lol_raises_when_not_linked(db_session):
    alice = _make_user("alice")
    db_session.add(alice)
    await db_session.commit()

    with pytest.raises(profile_service.RiotNotLinked):
        await profile_service.unlink_lol(db_session, alice.id)


# ----- get_profile + LoL stats degradation (HD-3) ----------------------

@pytest.mark.asyncio
async def test_get_profile_includes_lol_summary_when_linked(db_session):
    """get_profile compone summoner_level + masteries en el linked_game (contrato
    vigente LinkedGameSummary)."""
    from app.services.riot_api.client import ChampionMastery, SummonerProfile

    alice = _make_user("alice")
    db_session.add(alice)
    await db_session.commit()
    account = RiotAccount(user_id=alice.id, puuid="P1", game_name="Alice", tag_line="EUW", region="EUW1")
    db_session.add(account)
    await db_session.commit()

    client = MockRiotAPIClient()
    client.configured_summoner["P1"] = SummonerProfile(
        summoner_level=120, profile_icon_id=3, region="EUW1"
    )
    client.configured_mastery["P1"] = [ChampionMastery(7, 7, 100000)]

    profile = await profile_service.get_profile(db_session, alice.id, riot_client=client)

    assert len(profile.linked_games) == 1
    lol = profile.linked_games[0]
    assert lol.game == "lol"
    assert lol.region == "EUW1"
    assert lol.summoner_unavailable is False
    assert lol.summoner_level == 120
    assert lol.masteries_unavailable is False
    assert lol.masteries[0].champion_id == 7


@pytest.mark.asyncio
async def test_get_profile_marks_section_unavailable_on_partial_failure(db_session):
    """Degradación parcial (HD-3): si masteries falla, el linked_game la marca
    no disponible sin invalidar la parte de summoner."""
    from app.services.riot_api.client import SummonerProfile

    alice = _make_user("alice")
    db_session.add(alice)
    await db_session.commit()
    db_session.add(RiotAccount(user_id=alice.id, puuid="P1", game_name="Alice", tag_line="EUW", region="EUW1"))
    await db_session.commit()

    client = MockRiotAPIClient()
    client.configured_summoner["P1"] = SummonerProfile(
        summoner_level=50, profile_icon_id=1, region="EUW1"
    )
    # Mastery NOT seeded → mock raises RiotUnavailableError for that section.
    client.unavailable_methods["get_champion_mastery"] = {"P1"}

    profile = await profile_service.get_profile(db_session, alice.id, riot_client=client)

    lol = profile.linked_games[0]
    assert lol.summoner_unavailable is False
    assert lol.summoner_level == 50
    assert lol.masteries_unavailable is True
    assert lol.masteries == []


@pytest.mark.asyncio
async def test_get_profile_includes_ranked_and_recent_matches(db_session):
    """El linked_game compone ranked (league/v4) e historial (match/v5) cuando
    Riot responde; ambos visibles también en el perfil público (misma vía)."""
    from datetime import datetime, timezone

    from app.services.riot_api.client import (
        MatchSummary,
        RankedEntry,
        RankedStats,
        SummonerProfile,
    )

    alice = _make_user("alice")
    db_session.add(alice)
    await db_session.commit()
    db_session.add(RiotAccount(user_id=alice.id, puuid="P1", game_name="Alice", tag_line="EUW", region="EUW1"))
    await db_session.commit()

    client = MockRiotAPIClient()
    client.configured_summoner["P1"] = SummonerProfile(
        summoner_level=120, profile_icon_id=3, region="EUW1"
    )
    client.configured_mastery["P1"] = []
    client.configured_ranked["P1"] = RankedStats(
        solo_duo=RankedEntry("RANKED_SOLO_5x5", "GOLD", "II", 54, 30, 20),
        flex=None,
    )
    client.configured_matches["P1"] = [
        MatchSummary(
            match_id="EUW1_123",
            played_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
            duration_seconds=1830,
            champion_id=7,
            kills=8,
            deaths=2,
            assists=11,
            win=True,
            queue="CLASSIC",
        )
    ]

    profile = await profile_service.get_profile(db_session, alice.id, riot_client=client)

    lol = profile.linked_games[0]
    assert lol.ranked_unavailable is False
    assert lol.ranked_solo.tier == "GOLD"
    assert lol.ranked_solo.rank == "II"
    assert lol.ranked_solo.league_points == 54
    assert lol.ranked_solo.wins == 30
    assert lol.ranked_flex is None, "sin entrada flex → sin clasificar (no error)"

    assert lol.recent_matches_unavailable is False
    assert len(lol.recent_matches) == 1
    match = lol.recent_matches[0]
    assert match.match_id == "EUW1_123"
    assert match.win is True
    assert (match.kills, match.deaths, match.assists) == (8, 2, 11)
    assert match.champion_name, "el id de campeón se resuelve a nombre (ddragon)"


@pytest.mark.asyncio
async def test_get_profile_marks_ranked_and_matches_unavailable_on_failure(db_session):
    """Degradación parcial (HD-3) extendida: si league/v4 o match/v5 fallan,
    sus secciones se marcan no disponibles sin invalidar el resto."""
    from app.services.riot_api.client import SummonerProfile

    alice = _make_user("alice")
    db_session.add(alice)
    await db_session.commit()
    db_session.add(RiotAccount(user_id=alice.id, puuid="P1", game_name="Alice", tag_line="EUW", region="EUW1"))
    await db_session.commit()

    client = MockRiotAPIClient()
    client.configured_summoner["P1"] = SummonerProfile(
        summoner_level=50, profile_icon_id=1, region="EUW1"
    )
    client.configured_mastery["P1"] = []
    client.unavailable_methods["get_ranked_stats"] = {"P1"}
    client.unavailable_methods["get_recent_matches"] = {"P1"}

    profile = await profile_service.get_profile(db_session, alice.id, riot_client=client)

    lol = profile.linked_games[0]
    assert lol.summoner_level == 50
    assert lol.ranked_unavailable is True
    assert lol.ranked_solo is None and lol.ranked_flex is None
    assert lol.recent_matches_unavailable is True
    assert lol.recent_matches == []


@pytest.mark.asyncio
async def test_get_profile_no_lol_section_when_not_linked(db_session):
    alice = _make_user("alice")
    db_session.add(alice)
    await db_session.commit()

    client = MockRiotAPIClient()
    profile = await profile_service.get_profile(db_session, alice.id, riot_client=client)
    assert profile.linked_games == []


# ===== US3: delete_account =============================================

@pytest.mark.asyncio
async def test_delete_account_rejects_when_confirmation_does_not_match_nickname(db_session):
    alice = _make_user("alice")
    db_session.add(alice)
    await db_session.commit()

    with pytest.raises(profile_service.ConfirmationMismatch):
        await profile_service.delete_account(
            db_session, user_id=alice.id, confirmation="Alice", active_jtis=[]
        )

    refreshed = await db_session.get(User, alice.id)
    assert refreshed.nickname == "alice"
    assert refreshed.deleted_at is None


@pytest.mark.asyncio
async def test_delete_account_blocked_by_active_tournament(db_session):
    alice = _make_user("alice")
    db_session.add(alice)
    await db_session.commit()
    tournament = Tournament(
        name="t", format="round_robin", state="active", organizer_id=alice.id
    )
    db_session.add(tournament)
    await db_session.commit()
    db_session.add(Participant(tournament_id=tournament.id, user_id=alice.id))
    await db_session.commit()

    with pytest.raises(profile_service.DeleteAccountBlocked):
        await profile_service.delete_account(
            db_session, user_id=alice.id, confirmation="alice", active_jtis=[]
        )

    refreshed = await db_session.get(User, alice.id)
    assert refreshed.deleted_at is None


@pytest.mark.asyncio
async def test_delete_account_anonymizes_user_row(db_session):
    alice = _make_user("alice")
    alice.avatar_url = "https://cdn.example/me.png"
    alice.failed_login_attempts = 3
    db_session.add(alice)
    await db_session.commit()
    original_id = alice.id
    original_created_at = alice.created_at

    await profile_service.delete_account(
        db_session, user_id=alice.id, confirmation="alice", active_jtis=[]
    )

    refreshed = await db_session.get(User, original_id)
    assert refreshed.email is None
    assert refreshed.nickname.startswith("deleted-")
    assert refreshed.password_hash == "!"
    assert refreshed.failed_login_attempts == 0
    assert refreshed.locked_until is None
    assert refreshed.avatar_url is None
    assert refreshed.deleted_at is not None
    assert refreshed.id == original_id
    assert refreshed.created_at == original_created_at


@pytest.mark.asyncio
async def test_delete_account_removes_riot_account_row(db_session):
    alice = _make_user("alice")
    db_session.add(alice)
    await db_session.commit()
    db_session.add(RiotAccount(user_id=alice.id, puuid="P1", game_name="Alice", tag_line="EUW", region="EUW1"))
    await db_session.commit()

    await profile_service.delete_account(
        db_session, user_id=alice.id, confirmation="alice", active_jtis=[]
    )

    rows = (await db_session.execute(select(RiotAccount).where(RiotAccount.user_id == alice.id))).all()
    assert rows == []


@pytest.mark.asyncio
async def test_delete_account_invalidates_all_refresh_tokens(db_session):
    alice = _make_user("alice")
    db_session.add(alice)
    await db_session.commit()

    current_jti = uuid.uuid4()
    other_jti = uuid.uuid4()

    await profile_service.delete_account(
        db_session,
        user_id=alice.id,
        confirmation="alice",
        active_jtis=[current_jti, other_jti],
    )

    rows = (await db_session.execute(select(TokenBlacklist).where(TokenBlacklist.user_id == alice.id))).scalars().all()
    blacklisted = {row.jti for row in rows}
    assert current_jti in blacklisted, "even the current session must be invalidated"
    assert other_jti in blacklisted


@pytest.mark.asyncio
async def test_delete_account_bumps_password_changed_at(db_session):
    """M-01: borrar cuenta fija password_changed_at para que cualquier refresh
    previo (en otros dispositivos) sea rechazado por la regla HD-5."""
    alice = _make_user("alice")
    db_session.add(alice)
    await db_session.commit()
    assert alice.password_changed_at is None

    await profile_service.delete_account(
        db_session, user_id=alice.id, confirmation="alice", active_jtis=[]
    )

    refreshed = await db_session.get(User, alice.id)
    assert refreshed.password_changed_at is not None


@pytest.mark.asyncio
async def test_delete_account_blocks_future_login(db_session):
    alice = _make_user("alice", password="hunter2-abc")
    db_session.add(alice)
    await db_session.commit()
    user_id = alice.id

    await profile_service.delete_account(
        db_session, user_id=user_id, confirmation="alice", active_jtis=[]
    )

    refreshed = await db_session.get(User, user_id)
    assert security.verify_password("hunter2-abc", refreshed.password_hash) is False


@pytest.mark.asyncio
async def test_delete_account_allowed_when_only_finished_tournaments(db_session):
    alice = _make_user("alice")
    db_session.add(alice)
    await db_session.commit()
    tournament = Tournament(
        name="t", format="round_robin", state="finished", organizer_id=alice.id
    )
    db_session.add(tournament)
    await db_session.commit()
    db_session.add(Participant(tournament_id=tournament.id, user_id=alice.id))
    await db_session.commit()

    await profile_service.delete_account(
        db_session, user_id=alice.id, confirmation="alice", active_jtis=[]
    )

    refreshed = await db_session.get(User, alice.id)
    assert refreshed.deleted_at is not None
