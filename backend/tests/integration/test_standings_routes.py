"""Integration tests for /standings and /bracket (US4)."""
from __future__ import annotations

import pytest

from tests.helpers import register_user, switch_user


async def _make_active_round_robin(async_client, n: int = 4):
    organizer = await register_user(async_client, "org@example.com", "Org")
    t = (await async_client.post("/tournaments", json={"name": "T", "format": "round_robin"})).json()
    await async_client.post(f"/tournaments/{t['id']}/open")
    names = ["Alice", "Bob", "Carol", "Dave"]
    participants = []
    for i in range(n):
        u = await register_user(async_client, f"p{i}@example.com", names[i])
        switch_user(async_client, organizer)
        inv = (
            await async_client.post(
                f"/tournaments/{t['id']}/invitations",
                json={"invited_user_id": u["id"]},
            )
        ).json()
        switch_user(async_client, u)
        await async_client.post(f"/invitations/{inv['id']}/accept")
        participants.append(u)
    switch_user(async_client, organizer)
    await async_client.post(f"/tournaments/{t['id']}/start")
    return {"tournament": t, "organizer": organizer, "participants": participants}


@pytest.mark.asyncio
async def test_get_standings_round_robin_initial_zero_points(async_client):
    world = await _make_active_round_robin(async_client, n=4)
    resp = await async_client.get(f"/tournaments/{world['tournament']['id']}/standings")
    assert resp.status_code == 200
    standings = resp.json()
    assert len(standings) == 4
    assert all(s["points"] == 0 for s in standings)
    # Ranks must be 1..4 unique
    assert sorted(s["rank"] for s in standings) == [1, 2, 3, 4]


@pytest.mark.asyncio
async def test_get_standings_returns_404_for_single_elim(async_client):
    organizer = await register_user(async_client, "org@example.com", "Org")
    t = (await async_client.post("/tournaments", json={"name": "T", "format": "single_elim"})).json()
    resp = await async_client.get(f"/tournaments/{t['id']}/standings")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_bracket_returns_404_for_round_robin(async_client):
    organizer = await register_user(async_client, "org@example.com", "Org")
    t = (await async_client.post("/tournaments", json={"name": "T", "format": "round_robin"})).json()
    resp = await async_client.get(f"/tournaments/{t['id']}/bracket")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_schedule_distinguishes_pending_and_manual(async_client):
    world = await _make_active_round_robin(async_client, n=2)
    sched = (
        await async_client.get(f"/tournaments/{world['tournament']['id']}/schedule")
    ).json()
    assert any(m["state"] == "pending" for r in sched["rounds"] for m in r["matches"])

    # Resolve the only match manually.
    m = next(m for r in sched["rounds"] for m in r["matches"] if not m["is_bye"])
    resp = await async_client.post(
        f"/matches/{m['id']}/manual-result",
        json={"winner_participant_id": m["player1_id"]},
    )
    assert resp.status_code == 200

    sched = (
        await async_client.get(f"/tournaments/{world['tournament']['id']}/schedule")
    ).json()
    states = {m["state"] for r in sched["rounds"] for m in r["matches"]}
    assert "manual" in states
