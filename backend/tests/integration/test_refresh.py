from datetime import timedelta

from app.core import security


async def _register(client, email):
    response = await client.post(
        "/auth/register",
        json={"email": email, "password": "hunter2-abc", "nickname": email.split("@")[0].title()},
    )
    assert response.status_code == 201
    return response


async def test_refresh_rotates_tokens_and_blacklists_old_jti(async_client, db_session):
    from sqlalchemy import select

    from app.models.token_blacklist import TokenBlacklist

    await _register(async_client, "rotate@example.com")
    old_refresh = async_client.cookies.get("refresh_token")

    response = await async_client.post("/auth/refresh")
    assert response.status_code == 200

    new_refresh = async_client.cookies.get("refresh_token")
    assert new_refresh and new_refresh != old_refresh

    old_payload = security.verify_token(old_refresh, expected_type="refresh")
    result = await db_session.execute(select(TokenBlacklist).where(TokenBlacklist.jti == __import__("uuid").UUID(old_payload["jti"])))
    assert result.scalar_one_or_none() is not None


async def test_refresh_without_cookie_returns_401(async_client):
    response = await async_client.post("/auth/refresh")
    assert response.status_code == 401
    assert response.json() == {"detail": "Credenciales inválidas"}


async def test_reusing_rotated_refresh_returns_401(async_client):
    await _register(async_client, "reuse@example.com")
    old_refresh = async_client.cookies.get("refresh_token")

    first = await async_client.post("/auth/refresh")
    assert first.status_code == 200

    async_client.cookies.set("refresh_token", old_refresh)
    second = await async_client.post("/auth/refresh")
    assert second.status_code == 401


async def test_refresh_with_expired_token_returns_401(async_client):
    await _register(async_client, "expired@example.com")
    user_id = (await async_client.get("/auth/me")).json()["id"]

    expired, _ = security.create_refresh_token(subject=user_id, expires_delta=timedelta(seconds=-1))
    async_client.cookies.set("refresh_token", expired)

    response = await async_client.post("/auth/refresh")
    assert response.status_code == 401


async def test_refresh_with_access_token_as_refresh_returns_401(async_client):
    await _register(async_client, "mix@example.com")
    access = async_client.cookies.get("access_token")

    async_client.cookies.set("refresh_token", access)
    response = await async_client.post("/auth/refresh")
    assert response.status_code == 401
