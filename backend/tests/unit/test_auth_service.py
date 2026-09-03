import re

import pytest

from app.schemas.auth import RegisterRequest
from app.services import auth_service


async def test_generate_unique_nickname_returns_expected_format(db_session):
    nickname = await auth_service.generate_unique_nickname(db_session)
    assert re.fullmatch(r"user\d{5}", nickname)


async def test_generate_unique_nickname_retries_on_collision(db_session, monkeypatch):
    taken = {"user12345"}
    sequence = iter(["user12345", "user67890"])

    def _fake_randint(_low, _high):
        value = next(sequence)
        return int(value[4:])

    async def _exists(session, nickname):
        return nickname in taken

    monkeypatch.setattr(auth_service.random, "randint", _fake_randint)
    monkeypatch.setattr(auth_service, "_nickname_exists", _exists)

    nickname = await auth_service.generate_unique_nickname(db_session)
    assert nickname == "user67890"


async def test_register_user_persists_hash_not_plaintext(db_session):
    payload = RegisterRequest(email="alice@example.com", password="hunter2-abc", nickname="Alice")
    user = await auth_service.register_user(db_session, payload)
    assert user.email == "alice@example.com"
    assert user.nickname == "Alice"
    assert user.password_hash != "hunter2-abc"
    assert user.password_hash.startswith("$2")


async def test_register_user_assigns_auto_nickname_when_missing(db_session):
    payload = RegisterRequest(email="bob@example.com", password="hunter2-abc", nickname=None)
    user = await auth_service.register_user(db_session, payload)
    assert re.fullmatch(r"user\d{5}", user.nickname)


async def test_register_user_raises_on_duplicate_email(db_session):
    payload = RegisterRequest(email="dup@example.com", password="hunter2-abc", nickname="First")
    await auth_service.register_user(db_session, payload)
    dup = RegisterRequest(email="dup@example.com", password="hunter2-abc", nickname="Second")
    with pytest.raises(auth_service.EmailAlreadyRegistered):
        await auth_service.register_user(db_session, dup)


async def test_register_user_raises_on_duplicate_nickname(db_session):
    payload = RegisterRequest(email="a@example.com", password="hunter2-abc", nickname="Same")
    await auth_service.register_user(db_session, payload)
    dup = RegisterRequest(email="b@example.com", password="hunter2-abc", nickname="Same")
    with pytest.raises(auth_service.NicknameAlreadyTaken):
        await auth_service.register_user(db_session, dup)


async def test_authenticate_user_returns_user_on_correct_credentials(db_session):
    payload = RegisterRequest(email="c@example.com", password="hunter2-abc", nickname="Carol")
    created = await auth_service.register_user(db_session, payload)
    user = await auth_service.authenticate_user(db_session, "c@example.com", "hunter2-abc")
    assert user.id == created.id


async def test_authenticate_user_raises_on_unknown_email(db_session):
    with pytest.raises(auth_service.InvalidCredentials):
        await auth_service.authenticate_user(db_session, "nope@example.com", "whatever")


async def test_authenticate_user_raises_on_wrong_password(db_session):
    payload = RegisterRequest(email="d@example.com", password="hunter2-abc", nickname="Dave")
    await auth_service.register_user(db_session, payload)
    with pytest.raises(auth_service.InvalidCredentials):
        await auth_service.authenticate_user(db_session, "d@example.com", "wrong")


async def test_purge_expired_blacklist_removes_only_expired(db_session):
    """I-02: la purga elimina las entradas caducadas y conserva las vigentes."""
    import uuid
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import select

    from app.models.token_blacklist import TokenBlacklist
    from app.models.user import User

    user = User(email="p@example.com", nickname="Purge", password_hash="!")
    db_session.add(user)
    await db_session.commit()

    now = datetime.now(timezone.utc)
    expired_jti = uuid.uuid4()
    live_jti = uuid.uuid4()
    db_session.add_all(
        [
            TokenBlacklist(jti=expired_jti, user_id=user.id, expires_at=now - timedelta(hours=1)),
            TokenBlacklist(jti=live_jti, user_id=user.id, expires_at=now + timedelta(hours=1)),
        ]
    )
    await db_session.commit()

    deleted = await auth_service.purge_expired_blacklist(db_session, now=now)
    assert deleted == 1

    remaining = (await db_session.execute(select(TokenBlacklist.jti))).scalars().all()
    assert expired_jti not in remaining
    assert live_jti in remaining
