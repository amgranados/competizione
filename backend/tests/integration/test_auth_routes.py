import re
import statistics
import time

import pytest


def _parse_set_cookie_names(headers):
    names = []
    for raw in headers.get_list("set-cookie"):
        name = raw.split("=", 1)[0].strip()
        names.append(name)
    return names


def _set_cookie_for(headers, cookie_name):
    for raw in headers.get_list("set-cookie"):
        if raw.startswith(f"{cookie_name}="):
            return raw
    return None


async def test_register_with_email_password_creates_account(async_client):
    response = await async_client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": "hunter2-abc", "nickname": "Alice"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert body["nickname"] == "Alice"
    assert "id" in body

    names = _parse_set_cookie_names(response.headers)
    assert "access_token" in names
    assert "refresh_token" in names


async def test_register_without_nickname_assigns_auto_nickname(async_client):
    response = await async_client.post(
        "/auth/register",
        json={"email": "auto@example.com", "password": "hunter2-abc"},
    )
    assert response.status_code == 201
    assert re.fullmatch(r"user\d{5}", response.json()["nickname"])


async def test_register_duplicate_email_returns_409(async_client):
    payload = {"email": "dup@example.com", "password": "hunter2-abc", "nickname": "First"}
    first = await async_client.post("/auth/register", json=payload)
    assert first.status_code == 201
    second = await async_client.post(
        "/auth/register",
        json={"email": "dup@example.com", "password": "hunter2-abc", "nickname": "Second"},
    )
    assert second.status_code == 409


async def test_register_duplicate_nickname_returns_409(async_client):
    first = await async_client.post(
        "/auth/register",
        json={"email": "a@example.com", "password": "hunter2-abc", "nickname": "Same"},
    )
    assert first.status_code == 201
    second = await async_client.post(
        "/auth/register",
        json={"email": "b@example.com", "password": "hunter2-abc", "nickname": "Same"},
    )
    assert second.status_code == 409


async def test_register_short_password_returns_422(async_client):
    response = await async_client.post(
        "/auth/register",
        json={"email": "short@example.com", "password": "short", "nickname": "Short"},
    )
    assert response.status_code == 422


async def test_login_with_correct_credentials_returns_200_and_cookies(async_client):
    await async_client.post(
        "/auth/register",
        json={"email": "loginok@example.com", "password": "hunter2-abc", "nickname": "Login"},
    )
    response = await async_client.post(
        "/auth/login",
        json={"email": "loginok@example.com", "password": "hunter2-abc"},
    )
    assert response.status_code == 200
    names = _parse_set_cookie_names(response.headers)
    assert "access_token" in names
    assert "refresh_token" in names


async def test_login_with_wrong_password_returns_401_generic(async_client):
    await async_client.post(
        "/auth/register",
        json={"email": "wrongpw@example.com", "password": "hunter2-abc", "nickname": "Wrong"},
    )
    response = await async_client.post(
        "/auth/login",
        json={"email": "wrongpw@example.com", "password": "nope"},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Credenciales inválidas"}


async def test_login_with_unknown_email_returns_401_generic(async_client):
    response = await async_client.post(
        "/auth/login",
        json={"email": "doesnotexist@example.com", "password": "hunter2-abc"},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Credenciales inválidas"}


async def test_login_unknown_and_wrong_password_take_comparable_time(async_client):
    await async_client.post(
        "/auth/register",
        json={"email": "timing@example.com", "password": "hunter2-abc", "nickname": "Timing"},
    )

    async def _measure(email, password, n=5):
        samples = []
        for _ in range(n):
            start = time.perf_counter()
            await async_client.post("/auth/login", json={"email": email, "password": password})
            samples.append(time.perf_counter() - start)
        return statistics.median(samples)

    unknown = await _measure("nobody-timing@example.com", "hunter2-abc")
    wrong = await _measure("timing@example.com", "wrong-password")

    ratio = max(unknown, wrong) / max(min(unknown, wrong), 1e-6)
    assert ratio < 3.0, f"Timing ratio too large: unknown={unknown:.3f}s wrong={wrong:.3f}s"


async def test_auth_cookies_are_httponly_secure_samesite_lax(async_client):
    response = await async_client.post(
        "/auth/register",
        json={"email": "cookies@example.com", "password": "hunter2-abc", "nickname": "Cookies"},
    )
    assert response.status_code == 201

    for cookie_name in ("access_token", "refresh_token"):
        raw = _set_cookie_for(response.headers, cookie_name)
        assert raw is not None, f"missing Set-Cookie for {cookie_name}"
        lower = raw.lower()
        assert "httponly" in lower
        assert "secure" in lower
        assert "samesite=lax" in lower
        assert "path=/" in lower
