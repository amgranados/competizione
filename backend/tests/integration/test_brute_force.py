import pytest


@pytest.fixture
def disable_ip_rate_limit(monkeypatch):
    """Disable the slowapi IP limiter for tests that focus on per-account lockout."""
    from app.api.routes import auth as auth_routes

    monkeypatch.setattr(auth_routes, "IP_RATE_LIMIT_ENABLED", False)


async def test_ip_rate_limit_blocks_after_five_attempts_per_minute(async_client, monkeypatch):
    from app.api.routes import auth as auth_routes
    monkeypatch.setattr(auth_routes, "IP_RATE_LIMIT_ENABLED", True)
    auth_routes.limiter.reset()

    for i in range(5):
        r = await async_client.post("/auth/login", json={"email": f"nope{i}@example.com", "password": "whatever-long"})
        assert r.status_code == 401

    r = await async_client.post("/auth/login", json={"email": "again@example.com", "password": "whatever-long"})
    assert r.status_code == 429


async def test_register_is_rate_limited(async_client, monkeypatch):
    """L-01: /register también está limitado por IP (mismo patrón que login)."""
    from app.api.routes import auth as auth_routes
    monkeypatch.setattr(auth_routes, "IP_RATE_LIMIT_ENABLED", True)
    auth_routes.limiter.reset()

    nicknames = ["Alpha", "Bravo", "Charlie", "Delta", "Echo"]
    for i, nick in enumerate(nicknames):
        r = await async_client.post(
            "/auth/register",
            json={"email": f"reg{i}@example.com", "password": "hunter2-abc", "nickname": nick},
        )
        assert r.status_code == 201, r.text

    blocked = await async_client.post(
        "/auth/register",
        json={"email": "regblocked@example.com", "password": "hunter2-abc", "nickname": "Foxtrot"},
    )
    assert blocked.status_code == 429


async def test_register_duplicate_does_not_reveal_which_field(async_client):
    """L-01: el 409 de registro es genérico (no distingue email vs nickname)."""
    base = {"email": "dup@example.com", "password": "hunter2-abc", "nickname": "Dupe"}
    assert (await async_client.post("/auth/register", json=base)).status_code == 201

    by_email = await async_client.post(
        "/auth/register",
        json={"email": "dup@example.com", "password": "hunter2-abc", "nickname": "Other"},
    )
    by_nick = await async_client.post(
        "/auth/register",
        json={"email": "other@example.com", "password": "hunter2-abc", "nickname": "Dupe"},
    )
    assert by_email.status_code == 409
    assert by_nick.status_code == 409
    # Ambos devuelven exactamente el mismo detalle genérico.
    assert by_email.json()["detail"] == by_nick.json()["detail"]
    assert "email" not in by_email.json()["detail"].lower()
    assert "nickname" not in by_email.json()["detail"].lower()


async def test_account_locks_after_ten_failed_attempts(async_client, disable_ip_rate_limit):
    await async_client.post(
        "/auth/register",
        json={"email": "locktarget@example.com", "password": "hunter2-abc", "nickname": "Lockme"},
    )

    for _ in range(10):
        r = await async_client.post(
            "/auth/login",
            json={"email": "locktarget@example.com", "password": "wrong-pass"},
        )
        assert r.status_code == 401

    # 11th attempt with the CORRECT password must still be rejected with the generic error.
    r = await async_client.post(
        "/auth/login",
        json={"email": "locktarget@example.com", "password": "hunter2-abc"},
    )
    assert r.status_code == 401
    assert r.json() == {"detail": "Credenciales inválidas"}


async def test_successful_login_resets_failed_attempts(async_client, db_session, disable_ip_rate_limit):
    from sqlalchemy import select

    from app.models.user import User

    await async_client.post(
        "/auth/register",
        json={"email": "reset@example.com", "password": "hunter2-abc", "nickname": "Reset"},
    )

    for _ in range(9):
        await async_client.post(
            "/auth/login",
            json={"email": "reset@example.com", "password": "wrong-pass"},
        )

    ok = await async_client.post(
        "/auth/login",
        json={"email": "reset@example.com", "password": "hunter2-abc"},
    )
    assert ok.status_code == 200

    user = (await db_session.execute(select(User).where(User.email == "reset@example.com"))).scalar_one()
    await db_session.refresh(user)
    assert user.failed_login_attempts == 0
    assert user.locked_until is None


async def test_lock_expires_naturally(async_client, db_session, disable_ip_rate_limit, monkeypatch):
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import select

    from app.models.user import User

    await async_client.post(
        "/auth/register",
        json={"email": "expires@example.com", "password": "hunter2-abc", "nickname": "Expires"},
    )

    # Force the account into a locked state that already expired.
    user = (await db_session.execute(select(User).where(User.email == "expires@example.com"))).scalar_one()
    user.failed_login_attempts = 10
    user.locked_until = datetime.now(timezone.utc) - timedelta(minutes=1)
    await db_session.commit()

    r = await async_client.post(
        "/auth/login",
        json={"email": "expires@example.com", "password": "hunter2-abc"},
    )
    assert r.status_code == 200

    refreshed = (await db_session.execute(select(User).where(User.email == "expires@example.com"))).scalar_one()
    await db_session.refresh(refreshed)
    assert refreshed.locked_until is None
    assert refreshed.failed_login_attempts == 0
