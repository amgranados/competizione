"""Shared helpers for integration tests (feature 002)."""
from __future__ import annotations

from typing import Any


async def register_user(
    client,
    email: str,
    nickname: str,
    password: str = "hunter2-abc",
) -> dict[str, Any]:
    """Register a user via /auth/register and return its data + the cookies
    that identify it. After calling this, `client` carries the new user's
    cookies as the current session.
    """
    client.cookies.clear()
    response = await client.post(
        "/auth/register",
        json={"email": email, "password": password, "nickname": nickname},
    )
    assert response.status_code == 201, f"registration failed: {response.text}"
    payload = response.json()
    # Extract cookies from the Set-Cookie headers explicitly to avoid httpx
    # CookieConflict when the jar holds multiple cookies with the same name.
    cookies: dict[str, str] = {}
    for header in response.headers.get_list("set-cookie"):
        name_value = header.split(";", 1)[0]
        if "=" in name_value:
            name, value = name_value.split("=", 1)
            cookies[name.strip()] = value.strip()
    client.cookies.clear()
    for k, v in cookies.items():
        client.cookies.set(k, v)
    return {
        "id": payload["id"],
        "email": payload["email"],
        "nickname": payload["nickname"],
        "password": password,
        "cookies": cookies,
    }


def switch_user(client, user: dict[str, Any]) -> None:
    """Set the client's cookies to impersonate `user`."""
    client.cookies.clear()
    for name, value in user["cookies"].items():
        client.cookies.set(name, value)


def logout_client(client) -> None:
    client.cookies.clear()
