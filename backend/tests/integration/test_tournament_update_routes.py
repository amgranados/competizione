"""Integration tests for PATCH /tournaments/{id} (US5)."""
from __future__ import annotations

import pytest

from tests.helpers import make_invitable, register_user, switch_user


@pytest.mark.asyncio
async def test_rename_tournament_while_draft(async_client):
    organizer = await register_user(async_client, "org@example.com", "Org")
    t = (await async_client.post("/tournaments", json={"name": "Old", "format": "round_robin"})).json()
    resp = await async_client.patch(f"/tournaments/{t['id']}", json={"name": "New"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New"


@pytest.mark.asyncio
async def test_change_format_while_open(async_client):
    organizer = await register_user(async_client, "org@example.com", "Org")
    t = (await async_client.post("/tournaments", json={"name": "T", "format": "round_robin"})).json()
    await async_client.post(f"/tournaments/{t['id']}/open")
    resp = await async_client.patch(f"/tournaments/{t['id']}", json={"format": "single_elim"})
    assert resp.status_code == 200
    assert resp.json()["format"] == "single_elim"


@pytest.mark.asyncio
async def test_modify_after_start_returns_409(async_client, db_session):
    organizer = await register_user(async_client, "org@example.com", "Org")
    t = (await async_client.post("/tournaments", json={"name": "T", "format": "round_robin"})).json()
    await async_client.post(f"/tournaments/{t['id']}/open")
    # onboard 2 participants
    names = ["Alice", "Bob"]
    for i, n in enumerate(names):
        u = await register_user(async_client, f"p{i}@example.com", n)
        await make_invitable(db_session, organizer, u)
        switch_user(async_client, organizer)
        inv = (
            await async_client.post(
                f"/tournaments/{t['id']}/invitations",
                json={"invited_user_id": u["id"]},
            )
        ).json()
        switch_user(async_client, u)
        await async_client.post(f"/invitations/{inv['id']}/accept")
    switch_user(async_client, organizer)
    await async_client.post(f"/tournaments/{t['id']}/start")

    resp = await async_client.patch(f"/tournaments/{t['id']}", json={"name": "Late"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_modify_by_non_organizer_returns_403(async_client):
    organizer = await register_user(async_client, "org@example.com", "Org")
    t = (await async_client.post("/tournaments", json={"name": "T", "format": "round_robin"})).json()
    other = await register_user(async_client, "other@example.com", "Otrr")
    resp = await async_client.patch(f"/tournaments/{t['id']}", json={"name": "Hijack"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_modify_validation_rejects_invalid_format(async_client):
    organizer = await register_user(async_client, "org@example.com", "Org")
    t = (await async_client.post("/tournaments", json={"name": "T", "format": "round_robin"})).json()
    resp = await async_client.patch(f"/tournaments/{t['id']}", json={"format": "random"})
    assert resp.status_code == 422
