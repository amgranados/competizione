"""Shared helpers for integration tests (feature 002)."""
from __future__ import annotations

import uuid
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


async def link_riot(
    db_session,
    user: dict[str, Any],
    *,
    region: str = "EUW1",
) -> None:
    """Seed a linked Riot account for `user` (idempotent). Needed wherever the
    linked-LoL invariant applies: being invited or, as organizer, joining your
    own tournament."""
    from sqlalchemy import select

    from app.models.riot_account import RiotAccount

    user_id = uuid.UUID(user["id"])
    has_riot = (
        await db_session.execute(
            select(RiotAccount.id).where(RiotAccount.user_id == user_id)
        )
    ).first()
    if has_riot is None:
        db_session.add(
            RiotAccount(
                user_id=user_id,
                puuid=f"puuid-{user_id}",
                game_name=user["nickname"],
                tag_line="EUW",
                region=region,
            )
        )
        await db_session.commit()


async def make_invitable(
    db_session,
    inviter: dict[str, Any],
    invitee: dict[str, Any],
    *,
    region: str = "EUW1",
) -> None:
    """Satisfy the 004-add-friends precondition for inviting `invitee`.

    `tournament_service.invite` only allows inviting a user who is (1) an
    *accepted* friend of the inviter and (2) has a linked Riot account. This
    helper seeds both rows directly so invitation/start tests can focus on the
    behaviour under test. Idempotent per (inviter, invitee) pair.
    """
    from sqlalchemy import and_, or_, select

    from app.models.friendship import Friendship
    from app.models.riot_account import RiotAccount

    inviter_id = uuid.UUID(inviter["id"])
    invitee_id = uuid.UUID(invitee["id"])

    existing_friendship = (
        await db_session.execute(
            select(Friendship.id).where(
                Friendship.status == "accepted",
                or_(
                    and_(
                        Friendship.requester_id == inviter_id,
                        Friendship.addressee_id == invitee_id,
                    ),
                    and_(
                        Friendship.requester_id == invitee_id,
                        Friendship.addressee_id == inviter_id,
                    ),
                ),
            )
        )
    ).first()
    if existing_friendship is None:
        db_session.add(
            Friendship(
                requester_id=inviter_id,
                addressee_id=invitee_id,
                status="accepted",
            )
        )

    has_riot = (
        await db_session.execute(
            select(RiotAccount.id).where(RiotAccount.user_id == invitee_id)
        )
    ).first()
    if has_riot is None:
        db_session.add(
            RiotAccount(
                user_id=invitee_id,
                puuid=f"puuid-{invitee_id}",
                game_name=invitee["nickname"],
                tag_line="EUW",
                region=region,
            )
        )

    await db_session.commit()
