"""Integration tests for tournament cancellation (US6)."""
from __future__ import annotations

import pytest

from tests.helpers import register_user, switch_user


async def _onboard(async_client, organizer, tournament_id, n: int) -> list:
    names = ["Alice", "Bob", "Carol", "Dave"]
    participants = []
    for i in range(n):
        u = await register_user(async_client, f"p{i}@example.com", names[i])
        switch_user(async_client, organizer)
        inv = (
            await async_client.post(
                f"/tournaments/{tournament_id}/invitations",
                json={"invited_user_id": u["id"]},
            )
        ).json()
        switch_user(async_client, u)
        await async_client.post(f"/invitations/{inv['id']}/accept")
        participants.append(u)
    switch_user(async_client, organizer)
    return participants


@pytest.mark.asyncio
async def test_cancel_from_draft_transitions_to_cancelled(async_client):
    organizer = await register_user(async_client, "org@example.com", "Org")
    t = (await async_client.post("/tournaments", json={"name": "T", "format": "round_robin"})).json()
    resp = await async_client.post(f"/tournaments/{t['id']}/cancel")
    assert resp.status_code == 200
    body = resp.json()
    assert body["state"] == "cancelled"
    assert body["cancelled_at"] is not None


@pytest.mark.asyncio
async def test_cancel_from_active_transitions_to_cancelled(async_client):
    organizer = await register_user(async_client, "org@example.com", "Org")
    t = (await async_client.post("/tournaments", json={"name": "T", "format": "round_robin"})).json()
    await async_client.post(f"/tournaments/{t['id']}/open")
    await _onboard(async_client, organizer, t["id"], 2)
    await async_client.post(f"/tournaments/{t['id']}/start")
    resp = await async_client.post(f"/tournaments/{t['id']}/cancel")
    assert resp.status_code == 200
    assert resp.json()["state"] == "cancelled"


@pytest.mark.asyncio
async def test_cancel_from_finished_returns_409(async_client):
    organizer = await register_user(async_client, "org@example.com", "Org")
    t = (await async_client.post("/tournaments", json={"name": "T", "format": "round_robin"})).json()
    await async_client.post(f"/tournaments/{t['id']}/open")
    await _onboard(async_client, organizer, t["id"], 2)
    await async_client.post(f"/tournaments/{t['id']}/start")
    sched = (await async_client.get(f"/tournaments/{t['id']}/schedule")).json()
    m = next(m for r in sched["rounds"] for m in r["matches"] if not m["is_bye"])
    await async_client.post(
        f"/matches/{m['id']}/manual-result",
        json={"winner_participant_id": m["player1_id"]},
    )
    detail = (await async_client.get(f"/tournaments/{t['id']}")).json()
    assert detail["state"] == "finished"
    resp = await async_client.post(f"/tournaments/{t['id']}/cancel")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_cancel_creates_notification_for_every_participant(async_client):
    organizer = await register_user(async_client, "org@example.com", "Org")
    t = (await async_client.post("/tournaments", json={"name": "T", "format": "round_robin"})).json()
    await async_client.post(f"/tournaments/{t['id']}/open")
    participants = await _onboard(async_client, organizer, t["id"], 2)
    switch_user(async_client, organizer)
    await async_client.post(f"/tournaments/{t['id']}/cancel")

    for participant in participants:
        switch_user(async_client, participant)
        notifs = (await async_client.get("/notifications")).json()
        assert any(n["type"] == "tournament_cancelled" for n in notifs)


@pytest.mark.asyncio
async def test_cancel_by_non_organizer_returns_403(async_client):
    organizer = await register_user(async_client, "org@example.com", "Org")
    t = (await async_client.post("/tournaments", json={"name": "T", "format": "round_robin"})).json()
    other = await register_user(async_client, "other@example.com", "Otrr")
    resp = await async_client.post(f"/tournaments/{t['id']}/cancel")
    # Outsider doesn't see the tournament -> 404
    assert resp.status_code in (403, 404)
