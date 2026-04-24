async def test_auth_me_without_cookie_returns_401(async_client):
    response = await async_client.get("/auth/me")
    assert response.status_code == 401
    assert response.json() == {"detail": "Credenciales inválidas"}


async def test_auth_me_with_valid_cookie_returns_user(async_client):
    register = await async_client.post(
        "/auth/register",
        json={"email": "me@example.com", "password": "hunter2-abc", "nickname": "Me"},
    )
    assert register.status_code == 201
    created = register.json()

    response = await async_client.get("/auth/me")
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "me@example.com"
    assert body["nickname"] == "Me"
    assert body["id"] == created["id"]


async def test_auth_me_with_expired_access_cookie_returns_401(async_client):
    from datetime import timedelta

    from app.core import security

    register = await async_client.post(
        "/auth/register",
        json={"email": "exp@example.com", "password": "hunter2-abc", "nickname": "Exp"},
    )
    assert register.status_code == 201
    user_id = register.json()["id"]

    expired_access, _ = security.create_access_token(subject=user_id, expires_delta=timedelta(seconds=-1))
    async_client.cookies.set("access_token", expired_access)
    response = await async_client.get("/auth/me")
    assert response.status_code == 401


async def test_auth_me_with_refresh_cookie_as_access_returns_401(async_client):
    from app.core import security

    register = await async_client.post(
        "/auth/register",
        json={"email": "mix@example.com", "password": "hunter2-abc", "nickname": "Mix"},
    )
    assert register.status_code == 201
    user_id = register.json()["id"]

    refresh_as_access, _ = security.create_refresh_token(subject=user_id)
    async_client.cookies.clear()
    async_client.cookies.set("access_token", refresh_as_access)
    response = await async_client.get("/auth/me")
    assert response.status_code == 401
