"""Integration tests for /notifications (US1).

Covers T033-T035.
"""
from __future__ import annotations

import pytest

from tests.helpers import register_user, switch_user


@pytest.mark.asyncio
async def test_list_notifications_for_current_user(async_client):
    organizer = await register_user(async_client, "org@example.com", "Org")
    t = (await async_client.post("/tournaments", json={"name": "T", "format": "round_robin"})).json()
    await async_client.post(f"/tournaments/{t['id']}/open")

    invitee = await register_user(async_client, "inv@example.com", "Inv")
    switch_user(async_client, organizer)
    await async_client.post(
        f"/tournaments/{t['id']}/invitations", json={"invited_user_id": invitee["id"]}
    )

    switch_user(async_client, invitee)
    all_notifs = (await async_client.get("/notifications")).json()
    unread = (await async_client.get("/notifications?unread=true")).json()
    assert len(all_notifs) >= 1
    assert all(n["type"] == "invitation_received" for n in all_notifs)
    assert len(unread) == len(all_notifs)


@pytest.mark.asyncio
async def test_mark_notification_read(async_client):
    organizer = await register_user(async_client, "org@example.com", "Org")
    t = (await async_client.post("/tournaments", json={"name": "T", "format": "round_robin"})).json()
    await async_client.post(f"/tournaments/{t['id']}/open")
    invitee = await register_user(async_client, "inv@example.com", "Inv")
    switch_user(async_client, organizer)
    await async_client.post(
        f"/tournaments/{t['id']}/invitations", json={"invited_user_id": invitee["id"]}
    )

    switch_user(async_client, invitee)
    notif = (await async_client.get("/notifications")).json()[0]

    resp = await async_client.patch(f"/notifications/{notif['id']}/read")
    assert resp.status_code == 200
    assert resp.json()["read_at"] is not None

    unread = (await async_client.get("/notifications?unread=true")).json()
    assert all(n["id"] != notif["id"] for n in unread)


@pytest.mark.asyncio
async def test_mark_other_users_notification_returns_404(async_client):
    organizer = await register_user(async_client, "org@example.com", "Org")
    t = (await async_client.post("/tournaments", json={"name": "T", "format": "round_robin"})).json()
    await async_client.post(f"/tournaments/{t['id']}/open")
    invitee = await register_user(async_client, "inv@example.com", "Inv")
    switch_user(async_client, organizer)
    await async_client.post(
        f"/tournaments/{t['id']}/invitations", json={"invited_user_id": invitee["id"]}
    )

    switch_user(async_client, invitee)
    notif = (await async_client.get("/notifications")).json()[0]

    stranger = await register_user(async_client, "stranger@example.com", "Strangr")
    resp = await async_client.patch(f"/notifications/{notif['id']}/read")
    assert resp.status_code == 404
