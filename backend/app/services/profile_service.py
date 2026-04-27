"""Profile service — read & edit logic for the authenticated user (003-edit-profile)."""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.models.participant import Participant
from app.models.riot_account import RiotAccount
from app.models.token_blacklist import TokenBlacklist
from app.models.tournament import Tournament
from app.models.user import User
from app.schemas.profile import (
    ChampionMasteryEntry,
    LinkedGameSummary,
    ProfileBasic,
    ProfileResponse,
)
from app.services.riot_api import ddragon
from app.services.riot_api.client import RiotIdentityError, RiotUnavailableError
from app.services.riot_api.regions import platform_to_continent

logger = logging.getLogger(__name__)

_MIN_PASSWORD_LENGTH = 8
_MASTERY_DISPLAY_LIMIT = 10
_ACTIVE_TOURNAMENT_STATES = ("open", "in_progress")


# --- Domain exceptions ----------------------------------------------------

class NicknameAlreadyTaken(Exception):
    """Raised when attempting to set a nickname owned by another user."""


class WeakPasswordError(Exception):
    """Raised when a candidate password fails the policy validator."""


class InvalidCurrentPassword(Exception):
    """Raised when the supplied current password does not match."""


class RiotAlreadyLinked(Exception):
    """Raised when the user already has a RiotAccount and tries to link again."""


class RiotNotLinked(Exception):
    """Raised when unlink/lookup is attempted on a user without a RiotAccount."""


class RiotAccountAlreadyClaimed(Exception):
    """Raised when the resolved PUUID is already linked to a different user."""


class LinkAccountFailed(Exception):
    """Generic vinculación fail (HD-7) — Riot identity error or 4xx from Riot."""


class RiotUnavailable(Exception):
    """Riot API returned 5xx / timeout (HD-7)."""


class UnlinkBlocked(Exception):
    """User participates in an active tournament — cannot unlink (FR-014)."""


class ConfirmationMismatch(Exception):
    """The confirmation string did not match the current nickname (HD-2)."""


class DeleteAccountBlocked(Exception):
    """User participates in an active tournament — cannot delete (FR-023)."""


class UserNotFound(Exception):
    """The user_id does not match any user (or the user has been anonymized)."""


# --- Helpers --------------------------------------------------------------

async def _load_riot_account(session: AsyncSession, user_id: uuid.UUID) -> RiotAccount | None:
    result = await session.execute(select(RiotAccount).where(RiotAccount.user_id == user_id))
    return result.scalar_one_or_none()


async def _user_has_active_tournament(session: AsyncSession, user_id: uuid.UUID) -> bool:
    stmt = (
        select(Participant.id)
        .join(Tournament, Tournament.id == Participant.tournament_id)
        .where(
            Participant.user_id == user_id,
            Participant.removed.is_(False),
            Tournament.state.in_(_ACTIVE_TOURNAMENT_STATES),
        )
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.first() is not None


async def _build_lol_summary(riot_account: RiotAccount, riot_client) -> LinkedGameSummary:
    summary = LinkedGameSummary(
        game="lol",
        game_name=riot_account.game_name,
        tag_line=riot_account.tag_line,
        region=riot_account.region,
        linked_at=riot_account.linked_at,
    )
    if riot_client is None:
        return summary

    summoner_res, mastery_res = await asyncio.gather(
        riot_client.get_summoner_profile(riot_account.puuid, riot_account.region),
        riot_client.get_champion_mastery(
            riot_account.puuid, riot_account.region, _MASTERY_DISPLAY_LIMIT
        ),
        return_exceptions=True,
    )

    if isinstance(summoner_res, (RiotIdentityError, RiotUnavailableError)):
        logger.info(
            "summoner profile unavailable user_id=%s region=%s: %s",
            riot_account.user_id, riot_account.region, summoner_res,
        )
        summary.summoner_unavailable = True
    elif isinstance(summoner_res, BaseException):
        raise summoner_res
    else:
        summary.summoner_level = summoner_res.summoner_level
        summary.profile_icon_id = summoner_res.profile_icon_id
        summary.profile_icon_url = ddragon.profile_icon_url(summoner_res.profile_icon_id)

    if isinstance(mastery_res, (RiotIdentityError, RiotUnavailableError)):
        logger.info(
            "champion mastery unavailable user_id=%s region=%s: %s",
            riot_account.user_id, riot_account.region, mastery_res,
        )
        summary.masteries_unavailable = True
    elif isinstance(mastery_res, BaseException):
        raise mastery_res
    else:
        assets = await ddragon.champion_assets([m.champion_id for m in mastery_res])
        summary.masteries = [
            ChampionMasteryEntry(
                champion_id=m.champion_id,
                champion_name=assets[m.champion_id].name,
                champion_level=m.champion_level,
                champion_points=m.champion_points,
                image_url=assets[m.champion_id].image_url,
            )
            for m in mastery_res
        ]

    return summary


# --- Read APIs ------------------------------------------------------------

async def get_profile(
    session: AsyncSession, user_id: uuid.UUID, riot_client=None
) -> ProfileResponse:
    """Return the profile payload: basic data + linked games (with masteries)."""
    user = await session.get(User, user_id)
    if user is None:
        raise UserNotFound

    riot_account = await _load_riot_account(session, user_id)
    linked_games: list[LinkedGameSummary] = []
    if riot_account is not None:
        linked_games.append(await _build_lol_summary(riot_account, riot_client))

    return ProfileResponse(
        id=user.id,
        nickname=user.nickname,
        email=user.email,
        avatar_url=user.avatar_url,
        linked_games=linked_games,
    )


# --- Edit APIs (US1) ----------------------------------------------------

async def update_nickname(session: AsyncSession, user_id: uuid.UUID, new_nickname: str) -> User:
    """Set a new nickname, enforcing uniqueness across users (FR-005, FR-006)."""
    user = await session.get(User, user_id)
    if user is None:
        raise UserNotFound

    if user.nickname == new_nickname:
        return user

    existing = await session.execute(
        select(User.id).where(User.nickname == new_nickname, User.id != user_id)
    )
    if existing.first() is not None:
        raise NicknameAlreadyTaken

    user.nickname = new_nickname
    await session.commit()
    await session.refresh(user)
    return user


async def change_password(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    current_session_jti: uuid.UUID,
    current_password: str,
    new_password: str,
    active_jtis: Iterable[uuid.UUID] | None = None,
) -> User:
    """Verify current password, persist new hash, mark `password_changed_at`
    so OTHER refresh tokens issued before this moment are rejected at /refresh
    (HD-5). The current session is rotated by the caller (route layer) by
    issuing fresh access+refresh tokens whose `iat >= password_changed_at`.
    """
    if len(new_password) < _MIN_PASSWORD_LENGTH:
        raise WeakPasswordError

    user = await session.get(User, user_id)
    if user is None:
        raise UserNotFound

    if not security.verify_password(current_password, user.password_hash):
        raise InvalidCurrentPassword

    user.password_hash = security.hash_password(new_password)
    user.password_changed_at = datetime.now(timezone.utc)

    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    for jti in active_jtis or ():
        if jti == current_session_jti:
            continue
        session.add(TokenBlacklist(jti=jti, user_id=user_id, expires_at=expires_at))

    await session.commit()
    await session.refresh(user)
    return user


async def update_avatar(
    session: AsyncSession, user_id: uuid.UUID, avatar_url: str | None
) -> User:
    """Persist the avatar URL (or None to reset to default)."""
    user = await session.get(User, user_id)
    if user is None:
        raise UserNotFound

    user.avatar_url = avatar_url
    await session.commit()
    await session.refresh(user)
    return user


# --- US2: Riot account link / unlink -------------------------------------

async def link_lol(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    game_name: str,
    tag_line: str,
    region: str,
    riot_client,
) -> RiotAccount:
    """Verify the Riot ID via account/v1 (HTTP 200) and persist the link.

    `region` is a platform code (EUW1, NA1, KR, ...). It is mapped to the
    correct continent (americas/europe/asia) for the account/v1 call, and
    persisted as-is so champion-mastery/v4 can reach the right platform host.
    """
    existing = await _load_riot_account(session, user_id)
    if existing is not None:
        raise RiotAlreadyLinked

    try:
        continent = platform_to_continent(region)
    except ValueError as exc:
        raise LinkAccountFailed(str(exc)) from exc

    try:
        puuid = await riot_client.resolve_puuid(game_name, tag_line, continent)
    except RiotIdentityError as exc:
        logger.warning(
            "link_lol failed for user_id=%s region=%s continent=%s: %s",
            user_id, region, continent, exc,
        )
        raise LinkAccountFailed("Riot identity rejected") from exc
    except RiotUnavailableError as exc:
        logger.warning("link_lol unavailable user_id=%s: %s", user_id, exc)
        raise RiotUnavailable("Riot unavailable") from exc

    account = RiotAccount(
        user_id=user_id,
        puuid=puuid,
        game_name=game_name,
        tag_line=tag_line,
        region=region,
    )
    session.add(account)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise RiotAccountAlreadyClaimed("PUUID already linked to another user") from exc

    await session.refresh(account)
    logger.info("riot_account linked user_id=%s puuid=%s region=%s", user_id, puuid, region)
    return account


async def unlink_lol(session: AsyncSession, user_id: uuid.UUID) -> None:
    """Remove the user's RiotAccount unless they participate in an active LoL
    tournament (FR-014).
    """
    account = await _load_riot_account(session, user_id)
    if account is None:
        raise RiotNotLinked

    if await _user_has_active_tournament(session, user_id):
        raise UnlinkBlocked

    await session.delete(account)
    await session.commit()


# ===== US3: delete_account ==============================================

async def delete_account(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    confirmation: str,
    active_jtis: Iterable[uuid.UUID] | None = None,
) -> None:
    """Anonymize the user (HD-4) after validating confirmation (HD-2) and
    ensuring no active tournament participation (FR-023).
    """
    user = await session.get(User, user_id)
    if user is None:
        raise UserNotFound

    if confirmation != user.nickname:
        raise ConfirmationMismatch

    if await _user_has_active_tournament(session, user_id):
        raise DeleteAccountBlocked

    riot_account = await _load_riot_account(session, user_id)
    if riot_account is not None:
        await session.delete(riot_account)

    nickname_value = await _generate_deleted_nickname(session)

    user.email = None
    user.nickname = nickname_value
    user.password_hash = "!"
    user.failed_login_attempts = 0
    user.locked_until = None
    user.avatar_url = None
    user.deleted_at = datetime.now(timezone.utc)

    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    for jti in active_jtis or ():
        session.add(TokenBlacklist(jti=jti, user_id=user_id, expires_at=expires_at))

    await session.commit()
    logger.info("user_id=%s deleted (anonymized)", user_id)


async def _generate_deleted_nickname(session: AsyncSession) -> str:
    """Return a unique `deleted-XXXXXXXX` nickname (max 5 attempts)."""
    for _ in range(5):
        candidate = f"deleted-{uuid.uuid4().hex[:8]}"
        existing = await session.execute(select(User.id).where(User.nickname == candidate))
        if existing.first() is None:
            return candidate
    return f"deleted-{uuid.uuid4().hex}"
