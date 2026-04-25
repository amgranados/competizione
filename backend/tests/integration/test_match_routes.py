"""Integration tests for /matches/* (US3).

Covers T072-T074.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.match import Match
from tests.helpers import register_user, switch_user


async def _tournament_with_4_participants(async_client):
    organizer = await register_user(async_client, "org@example.com", "Org")
    t = (await async_client.post("/tournaments", json={"name": "T", "format": "single_elim"})).json()
    await async_client.post(f"/tournaments/{t['id']}/open")
    names = ["Alice", "Bob", "Carol", "Dave"]
    participants = []
    for i, n in enumerate(names):
        user = await register_user(async_client, f"p{i}@example.com", n)
        switch_user(async_client, organizer)
        inv = (
            await async_client.post(
                f"/tournaments/{t['id']}/invitations",
                json={"invited_user_id": user["id"]},
            )
        ).json()
        switch_user(async_client, user)
        await async_client.post(f"/invitations/{inv['id']}/accept")
        participants.append(user)
    switch_user(async_client, organizer)
    await async_client.post(f"/tournaments/{t['id']}/start")
    return {"tournament": t, "organizer": organizer, "participants": participants}


@pytest.mark.asyncio
async def test_manual_result_route_returns_match_with_tag(async_client, db_session):
    world = await _tournament_with_4_participants(async_client)
    sched = (await async_client.get(f"/tournaments/{world['tournament']['id']}/schedule")).json()
    m = next(m for r in sched["rounds"] for m in r["matches"] if not m["is_bye"])

    resp = await async_client.post(
        f"/matches/{m['id']}/manual-result",
        json={"winner_participant_id": m["player1_id"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["state"] == "manual"
    assert body["winner_participant_id"] == m["player1_id"]


@pytest.mark.asyncio
async def test_manual_result_route_organizer_only(async_client):
    world = await _tournament_with_4_participants(async_client)
    sched = (await async_client.get(f"/tournaments/{world['tournament']['id']}/schedule")).json()
    m = next(m for r in sched["rounds"] for m in r["matches"] if not m["is_bye"])

    # switch to a non-organizer (a participant)
    switch_user(async_client, world["participants"][0])
    resp = await async_client.post(
        f"/matches/{m['id']}/manual-result",
        json={"winner_participant_id": m["player1_id"]},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_manual_result_route_requires_auth(async_client):
    world = await _tournament_with_4_participants(async_client)
    sched = (await async_client.get(f"/tournaments/{world['tournament']['id']}/schedule")).json()
    m = next(m for r in sched["rounds"] for m in r["matches"] if not m["is_bye"])
    async_client.cookies.clear()
    resp = await async_client.post(
        f"/matches/{m['id']}/manual-result",
        json={"winner_participant_id": m["player1_id"]},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_match_hides_tournament_code_for_non_player(async_client):
    world = await _tournament_with_4_participants(async_client)
    sched = (await async_client.get(f"/tournaments/{world['tournament']['id']}/schedule")).json()
    # Pick match between participants[0] and participants[1]
    non_player = world["participants"][2]  # not in m1
    m = None
    for round in sched["rounds"]:
        for match in round["matches"]:
            if match["is_bye"]:
                continue
            # choose the match where non_player is neither participant
            # we don't know user ids directly here - use schedule player1/player2 vs participants
            players = {match["player1_id"], match["player2_id"]}
            if match["player1_id"] and match["player2_id"]:
                m = match
                break
        if m:
            break
    assert m is not None
    # As organizer, tournament_code is visible
    assert m["tournament_code"] is not None

    # As a participant who is not a player of the match, code must be hidden.
    # Find a participant who is NOT player1/player2 of m.
    # easiest: switch to any participant and test schedule-level visibility.
    # We'll pick one explicitly by matching nickname.
    # Participant IDs are not directly returned, but the organizer's view exposes them.
    detail = (await async_client.get(f"/tournaments/{world['tournament']['id']}")).json()
    participants_index = {p["user_id"]: p["id"] for p in detail["participants"]}
    match_player_ids = {m["player1_id"], m["player2_id"]}
    non_player_user = next(
        u for u in world["participants"] if participants_index[u["id"]] not in match_player_ids
    )
    switch_user(async_client, non_player_user)
    resp = await async_client.get(f"/matches/{m['id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["tournament_code"] is None


@pytest.mark.asyncio
async def test_manual_result_with_invalid_winner_returns_409(async_client):
    world = await _tournament_with_4_participants(async_client)
    sched = (await async_client.get(f"/tournaments/{world['tournament']['id']}/schedule")).json()
    m = next(m for r in sched["rounds"] for m in r["matches"] if not m["is_bye"])
    # Use the organizer as "winner" — won't be a player of the match
    # We don't have easy access to participant IDs outside the match, so
    # pick any non-player participant id via the tournament detail.
    detail = (await async_client.get(f"/tournaments/{world['tournament']['id']}")).json()
    other_pid = next(
        p["id"] for p in detail["participants"]
        if p["id"] not in (m["player1_id"], m["player2_id"])
    )
    resp = await async_client.post(
        f"/matches/{m['id']}/manual-result",
        json={"winner_participant_id": other_pid},
    )
    assert resp.status_code == 409
