import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

TokenType = Literal["access", "refresh"]

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_DUMMY_HASH = _pwd_context.hash("x" * 12)


class InvalidToken(Exception):
    pass


def get_secret() -> str:
    return get_settings().SECRET_KEY


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _pwd_context.verify(plain, hashed)
    except ValueError:
        return False


def dummy_verify() -> None:
    """Run a bcrypt verification against a throwaway hash to equalize latency
    when the target account does not exist (mitigates login timing oracle)."""
    _pwd_context.verify("x", _DUMMY_HASH)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(*, subject: str, expires_delta: timedelta | None = None) -> tuple[str, str]:
    settings = get_settings()
    expire = _now() + (expires_delta if expires_delta is not None else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    jti = str(uuid.uuid4())
    payload = {
        "sub": subject,
        "type": "access",
        "iat": int(_now().timestamp()),
        "exp": int(expire.timestamp()),
        "jti": jti,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return token, jti


def create_refresh_token(*, subject: str, expires_delta: timedelta | None = None) -> tuple[str, str]:
    settings = get_settings()
    expire = _now() + (expires_delta if expires_delta is not None else timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
    jti = str(uuid.uuid4())
    payload = {
        "sub": subject,
        "type": "refresh",
        "iat": int(_now().timestamp()),
        "exp": int(expire.timestamp()),
        "jti": jti,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return token, jti


def verify_token(token: str, *, expected_type: TokenType) -> dict:
    try:
        payload = jwt.decode(token, get_secret(), algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise InvalidToken(str(exc)) from exc

    if payload.get("type") != expected_type:
        raise InvalidToken(f"expected token type {expected_type}, got {payload.get('type')}")

    return payload


def access_token_max_age_seconds() -> int:
    return get_settings().ACCESS_TOKEN_EXPIRE_MINUTES * 60


def refresh_token_max_age_seconds() -> int:
    return get_settings().REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60


async def get_current_user(request, session):
    """FastAPI dependency — imported through a wrapper in app.api.routes.auth to
    keep model imports out of the security module."""
    from sqlalchemy import select

    from app.models.user import User

    token = request.cookies.get("access_token")
    if not token:
        raise InvalidToken("missing access_token cookie")

    payload = verify_token(token, expected_type="access")
    subject = payload.get("sub")
    if not subject:
        raise InvalidToken("missing subject")

    result = await session.execute(select(User).where(User.id == uuid.UUID(subject)))
    user = result.scalar_one_or_none()
    if user is None:
        raise InvalidToken("user not found")
    return user
