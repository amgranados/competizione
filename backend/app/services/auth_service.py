import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.models.token_blacklist import TokenBlacklist
from app.models.user import User
from app.schemas.auth import RegisterRequest


class EmailAlreadyRegistered(Exception):
    pass


class NicknameAlreadyTaken(Exception):
    pass


class NicknameGenerationExhausted(Exception):
    pass


class InvalidCredentials(Exception):
    pass


_MAX_NICKNAME_ATTEMPTS = 10


async def _nickname_exists(session: AsyncSession, nickname: str) -> bool:
    result = await session.execute(select(User.id).where(User.nickname == nickname))
    return result.first() is not None


async def _email_exists(session: AsyncSession, email: str) -> bool:
    result = await session.execute(select(User.id).where(User.email == email))
    return result.first() is not None


async def generate_unique_nickname(session: AsyncSession) -> str:
    for _ in range(_MAX_NICKNAME_ATTEMPTS):
        candidate = f"user{random.randint(10000, 99999)}"
        if not await _nickname_exists(session, candidate):
            return candidate
    raise NicknameGenerationExhausted


async def register_user(session: AsyncSession, payload: RegisterRequest) -> User:
    if await _email_exists(session, payload.email):
        raise EmailAlreadyRegistered

    nickname = payload.nickname
    if nickname is None:
        nickname = await generate_unique_nickname(session)
    elif await _nickname_exists(session, nickname):
        raise NicknameAlreadyTaken

    user = User(
        email=payload.email,
        nickname=nickname,
        password_hash=security.hash_password(payload.password),
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        message = str(exc.orig).lower() if exc.orig else str(exc).lower()
        if "email" in message:
            raise EmailAlreadyRegistered from exc
        if "nickname" in message:
            raise NicknameAlreadyTaken from exc
        raise

    await session.refresh(user)
    return user


_FAILED_ATTEMPTS_THRESHOLD = 10
_LOCKOUT_MINUTES = 15


async def authenticate_user(session: AsyncSession, email: str, password: str) -> User:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        security.dummy_verify()
        raise InvalidCredentials

    now = datetime.now(timezone.utc)
    locked = user.locked_until
    # SQLite may return naive datetimes; normalize to UTC for comparison.
    if locked is not None and locked.tzinfo is None:
        locked = locked.replace(tzinfo=timezone.utc)

    if locked is not None and locked > now:
        # Account is currently locked. Do NOT reveal, and do NOT even verify the password.
        raise InvalidCredentials

    if locked is not None and locked <= now:
        user.locked_until = None
        user.failed_login_attempts = 0

    if not security.verify_password(password, user.password_hash):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= _FAILED_ATTEMPTS_THRESHOLD:
            user.locked_until = now + timedelta(minutes=_LOCKOUT_MINUTES)
        await session.commit()
        raise InvalidCredentials

    user.failed_login_attempts = 0
    user.locked_until = None
    await session.commit()
    await session.refresh(user)
    return user


async def _is_jti_blacklisted(session: AsyncSession, jti: uuid.UUID) -> bool:
    result = await session.execute(select(TokenBlacklist.jti).where(TokenBlacklist.jti == jti))
    return result.first() is not None


async def _blacklist_jti(session: AsyncSession, *, jti: uuid.UUID, user_id: uuid.UUID, exp_timestamp: int) -> None:
    expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
    session.add(TokenBlacklist(jti=jti, user_id=user_id, expires_at=expires_at))


async def refresh_session(session: AsyncSession, refresh_cookie: str | None) -> tuple[User, str, str]:
    """Verify a refresh token, rotate it (old jti → blacklist) and emit a new pair."""
    if not refresh_cookie:
        raise InvalidCredentials

    try:
        payload = security.verify_token(refresh_cookie, expected_type="refresh")
    except security.InvalidToken as exc:
        raise InvalidCredentials from exc

    try:
        jti = uuid.UUID(payload["jti"])
        subject = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise InvalidCredentials from exc

    if await _is_jti_blacklisted(session, jti):
        raise InvalidCredentials

    user = await session.get(User, subject)
    if user is None:
        raise InvalidCredentials

    # HD-5: reject refresh tokens issued before the most recent password change.
    pwd_changed = user.password_changed_at
    if pwd_changed is not None:
        if pwd_changed.tzinfo is None:
            pwd_changed = pwd_changed.replace(tzinfo=timezone.utc)
        if payload.get("iat", 0) < int(pwd_changed.timestamp()):
            raise InvalidCredentials

    await _blacklist_jti(session, jti=jti, user_id=subject, exp_timestamp=payload["exp"])

    access_token, _ = security.create_access_token(subject=str(subject))
    new_refresh, _ = security.create_refresh_token(subject=str(subject))

    await session.commit()
    await session.refresh(user)
    return user, access_token, new_refresh


async def logout_session(session: AsyncSession, refresh_cookie: str | None) -> None:
    """Best-effort logout: if the refresh token is valid and not blacklisted, blacklist its jti."""
    if not refresh_cookie:
        return
    try:
        payload = security.verify_token(refresh_cookie, expected_type="refresh")
    except security.InvalidToken:
        return
    try:
        jti = uuid.UUID(payload["jti"])
        subject = uuid.UUID(payload["sub"])
        exp = payload["exp"]
    except (KeyError, ValueError):
        return
    if await _is_jti_blacklisted(session, jti):
        return
    await _blacklist_jti(session, jti=jti, user_id=subject, exp_timestamp=exp)
    await session.commit()
