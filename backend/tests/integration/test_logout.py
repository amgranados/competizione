async def test_logout_returns_204_and_clears_cookies(async_client):
    await async_client.post(
        "/auth/register",
        json={"email": "out@example.com", "password": "hunter2-abc", "nickname": "Out"},
    )
    response = await async_client.post("/auth/logout")
    assert response.status_code == 204

    cleared_raw = {line.split("=", 1)[0]: line for line in response.headers.get_list("set-cookie")}
    assert "access_token" in cleared_raw
    assert "refresh_token" in cleared_raw
    for raw in cleared_raw.values():
        assert "Max-Age=0" in raw


async def test_after_logout_reusing_refresh_returns_401(async_client):
    await async_client.post(
        "/auth/register",
        json={"email": "reuse@example.com", "password": "hunter2-abc", "nickname": "Reuse"},
    )
    old_refresh = async_client.cookies.get("refresh_token")

    logout = await async_client.post("/auth/logout")
    assert logout.status_code == 204

    async_client.cookies.set("refresh_token", old_refresh)
    reuse = await async_client.post("/auth/refresh")
    assert reuse.status_code == 401


async def test_after_logout_access_cookie_is_cleared(async_client):
    await async_client.post(
        "/auth/register",
        json={"email": "clear@example.com", "password": "hunter2-abc", "nickname": "Clear"},
    )
    # /auth/me should work right after register
    me_before = await async_client.get("/auth/me")
    assert me_before.status_code == 200

    await async_client.post("/auth/logout")

    # httpx respects Max-Age=0 and drops the cookie, so the follow-up /auth/me has no access cookie.
    me_after = await async_client.get("/auth/me")
    assert me_after.status_code == 401
