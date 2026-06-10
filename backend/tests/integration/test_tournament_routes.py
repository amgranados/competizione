"""Integration tests for tournament routes (US1).

Covers T017-T032: create tournament, state transitions, invitations, accept/
reject/cancel, participant removal, start (round-robin + single-elim),
authorization boundaries.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from tests.helpers import make_invitable, register_user, switch_user


@pytest.mark.asyncio
async def test_create_tournament_as_draft(async_client):
    organizer = await register_user(async_client, "org@example.com", "Org")

    resp = await async_client.post(
        "/tournaments",
        json={"name": "Mi Torneo", "format": "round_robin"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Mi Torneo"
    assert body["state"] == "draft"
    assert body["format"] == "round_robin"
    assert body["organizer_id"] == organizer["id"]


@pytest.mark.asyncio
async def test_create_tournament_rejects_invalid_format(async_client):
    await register_user(async_client, "org@example.com", "Org")
    resp = await async_client.post(
        "/tournaments",
        json={"name": "X", "format": "random"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_tournament_rejects_empty_name(async_client):
    await register_user(async_client, "org@example.com", "Org")
    resp = await async_client.post(
        "/tournaments",
        json={"name": "   ", "format": "round_robin"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_open_registration_draft_to_open(async_client):
    await register_user(async_client, "org@example.com", "Org")
    created = (await async_client.post("/tournaments", json={"name": "T", "format": "round_robin"})).json()

    resp = await async_client.post(f"/tournaments/{created['id']}/open")
    assert resp.status_code == 200
    assert resp.json()["state"] == "open"


@pytest.mark.asyncio
async def test_open_registration_from_wrong_state_returns_409(async_client):
    await register_user(async_client, "org@example.com", "Org")
    created = (await async_client.post("/tournaments", json={"name": "T", "format": "round_robin"})).json()
    await async_client.post(f"/tournaments/{created['id']}/open")

    resp = await async_client.post(f"/tournaments/{created['id']}/open")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_invite_user_creates_pending_invitation_with_48h_expiry(async_client, db_session):
    organizer = await register_user(async_client, "org@example.com", "Org")
    t = (await async_client.post("/tournaments", json={"name": "T", "format": "round_robin"})).json()
    await async_client.post(f"/tournaments/{t['id']}/open")

    invitee = await register_user(async_client, "inv@example.com", "Invitee")
    await make_invitable(db_session, organizer, invitee)
    switch_user(async_client, organizer)

    resp = await async_client.post(
        f"/tournaments/{t['id']}/invitations",
        json={"invited_user_id": invitee["id"]},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["state"] == "pending"
    created_at = datetime.fromisoformat(body["created_at"].replace("Z", "+00:00"))
    expires_at = datetime.fromisoformat(body["expires_at"].replace("Z", "+00:00"))
    delta = expires_at - created_at
    assert abs(delta - timedelta(hours=48)).total_seconds() < 5

    switch_user(async_client, invitee)
    notif_resp = await async_client.get("/notifications?unread=true")
    assert notif_resp.status_code == 200
    types = [n["type"] for n in notif_resp.json()]
    assert "invitation_received" in types


@pytest.mark.asyncio
async def test_cannot_invite_same_user_twice_while_pending(async_client, db_session):
    organizer = await register_user(async_client, "org@example.com", "Org")
    t = (await async_client.post("/tournaments", json={"name": "T", "format": "round_robin"})).json()
    await async_client.post(f"/tournaments/{t['id']}/open")
    invitee = await register_user(async_client, "inv@example.com", "Inv")
    await make_invitable(db_session, organizer, invitee)
    switch_user(async_client, organizer)

    first = await async_client.post(
        f"/tournaments/{t['id']}/invitations", json={"invited_user_id": invitee["id"]}
    )
    assert first.status_code == 201
    second = await async_client.post(
        f"/tournaments/{t['id']}/invitations", json={"invited_user_id": invitee["id"]}
    )
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_accept_invitation_creates_participant(async_client, db_session):
    organizer = await register_user(async_client, "org@example.com", "Org")
    t = (await async_client.post("/tournaments", json={"name": "T", "format": "round_robin"})).json()
    await async_client.post(f"/tournaments/{t['id']}/open")
    invitee = await register_user(async_client, "inv@example.com", "Inv")
    await make_invitable(db_session, organizer, invitee)
    switch_user(async_client, organizer)
    inv = (
        await async_client.post(
            f"/tournaments/{t['id']}/invitations", json={"invited_user_id": invitee["id"]}
        )
    ).json()

    switch_user(async_client, invitee)
    resp = await async_client.post(f"/invitations/{inv['id']}/accept")
    assert resp.status_code == 200
    assert resp.json()["state"] == "accepted"

    switch_user(async_client, organizer)
    detail = (await async_client.get(f"/tournaments/{t['id']}")).json()
    assert any(p["user_id"] == invitee["id"] for p in detail["participants"])

    notif_types = [n["type"] for n in (await async_client.get("/notifications")).json()]
    assert "invitation_accepted" in notif_types


@pytest.mark.asyncio
async def test_reject_invitation(async_client, db_session):
    organizer = await register_user(async_client, "org@example.com", "Org")
    t = (await async_client.post("/tournaments", json={"name": "T", "format": "round_robin"})).json()
    await async_client.post(f"/tournaments/{t['id']}/open")
    invitee = await register_user(async_client, "inv@example.com", "Inv")
    await make_invitable(db_session, organizer, invitee)
    switch_user(async_client, organizer)
    inv = (
        await async_client.post(
            f"/tournaments/{t['id']}/invitations", json={"invited_user_id": invitee["id"]}
        )
    ).json()

    switch_user(async_client, invitee)
    resp = await async_client.post(f"/invitations/{inv['id']}/reject")
    assert resp.status_code == 200
    assert resp.json()["state"] == "rejected"

    switch_user(async_client, organizer)
    notif_types = [n["type"] for n in (await async_client.get("/notifications")).json()]
    assert "invitation_rejected" in notif_types


@pytest.mark.asyncio
async def test_cancel_pending_invitation_by_organizer(async_client, db_session):
    organizer = await register_user(async_client, "org@example.com", "Org")
    t = (await async_client.post("/tournaments", json={"name": "T", "format": "round_robin"})).json()
    await async_client.post(f"/tournaments/{t['id']}/open")
    invitee = await register_user(async_client, "inv@example.com", "Inv")
    await make_invitable(db_session, organizer, invitee)
    switch_user(async_client, organizer)
    inv = (
        await async_client.post(
            f"/tournaments/{t['id']}/invitations", json={"invited_user_id": invitee["id"]}
        )
    ).json()

    resp = await async_client.post(
        f"/tournaments/{t['id']}/invitations/{inv['id']}/cancel"
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == "cancelled"

    switch_user(async_client, invitee)
    notif_types = [n["type"] for n in (await async_client.get("/notifications")).json()]
    assert "invitation_cancelled" in notif_types


@pytest.mark.asyncio
async def test_accept_expired_invitation_returns_410(async_client, db_session):
    from sqlalchemy import select

    from app.models.invitation import Invitation

    organizer = await register_user(async_client, "org@example.com", "Org")
    t = (await async_client.post("/tournaments", json={"name": "T", "format": "round_robin"})).json()
    await async_client.post(f"/tournaments/{t['id']}/open")
    invitee = await register_user(async_client, "inv@example.com", "Inv")
    await make_invitable(db_session, organizer, invitee)
    switch_user(async_client, organizer)
    inv = (
        await async_client.post(
            f"/tournaments/{t['id']}/invitations", json={"invited_user_id": invitee["id"]}
        )
    ).json()

    # backdate expiration to a past instant
    result = await db_session.execute(select(Invitation).where(Invitation.id.is_not(None)))
    row = result.scalars().first()
    row.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    await db_session.commit()

    switch_user(async_client, invitee)
    resp = await async_client.post(f"/invitations/{inv['id']}/accept")
    assert resp.status_code == 410


@pytest.mark.asyncio
async def test_remove_participant_while_draft(async_client, db_session):
    organizer = await register_user(async_client, "org@example.com", "Org")
    t = (await async_client.post("/tournaments", json={"name": "T", "format": "round_robin"})).json()
    await async_client.post(f"/tournaments/{t['id']}/open")
    invitee = await register_user(async_client, "inv@example.com", "Inv")
    await make_invitable(db_session, organizer, invitee)
    switch_user(async_client, organizer)
    inv = (
        await async_client.post(
            f"/tournaments/{t['id']}/invitations", json={"invited_user_id": invitee["id"]}
        )
    ).json()

    switch_user(async_client, invitee)
    await async_client.post(f"/invitations/{inv['id']}/accept")

    switch_user(async_client, organizer)
    detail = (await async_client.get(f"/tournaments/{t['id']}")).json()
    participant_id = [p["id"] for p in detail["participants"] if p["user_id"] == invitee["id"]][0]

    resp = await async_client.delete(
        f"/tournaments/{t['id']}/participants/{participant_id}"
    )
    assert resp.status_code == 204

    detail = (await async_client.get(f"/tournaments/{t['id']}")).json()
    assert not any(p["user_id"] == invitee["id"] for p in detail["participants"])


@pytest.mark.asyncio
async def test_start_tournament_rejects_below_minimum(async_client):
    organizer = await register_user(async_client, "org@example.com", "Org")
    t = (await async_client.post("/tournaments", json={"name": "T", "format": "round_robin"})).json()
    await async_client.post(f"/tournaments/{t['id']}/open")

    # 0 participants
    resp = await async_client.post(f"/tournaments/{t['id']}/start")
    assert resp.status_code == 409


async def _onboard_participants(
    async_client, db_session, organizer, tournament_id: str, n: int
) -> list[dict]:
    names = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Hank"]
    participants = []
    for i in range(n):
        user = await register_user(async_client, f"p{i}@example.com", names[i])
        await make_invitable(db_session, organizer, user)
        switch_user(async_client, organizer)
        inv = (
            await async_client.post(
                f"/tournaments/{tournament_id}/invitations",
                json={"invited_user_id": user["id"]},
            )
        ).json()
        switch_user(async_client, user)
        await async_client.post(f"/invitations/{inv['id']}/accept")
        participants.append(user)
    switch_user(async_client, organizer)
    return participants


@pytest.mark.asyncio
async def test_start_round_robin_generates_all_matches_and_codes(async_client, db_session):
    organizer = await register_user(async_client, "org@example.com", "Org")
    t = (await async_client.post("/tournaments", json={"name": "T", "format": "round_robin"})).json()
    await async_client.post(f"/tournaments/{t['id']}/open")
    await _onboard_participants(async_client, db_session, organizer, t["id"], 4)

    resp = await async_client.post(f"/tournaments/{t['id']}/start")
    assert resp.status_code == 200
    assert resp.json()["state"] == "active"

    sched = (await async_client.get(f"/tournaments/{t['id']}/schedule")).json()
    assert sched["format"] == "round_robin"
    assert len(sched["rounds"]) == 3
    codes = [m["id"] for r in sched["rounds"] for m in r["matches"] if not m["is_bye"]]
    assert len(codes) == 6


@pytest.mark.asyncio
async def test_start_single_elim_generates_first_round_with_byes(async_client, db_session):
    organizer = await register_user(async_client, "org@example.com", "Org")
    t = (await async_client.post("/tournaments", json={"name": "T", "format": "single_elim"})).json()
    await async_client.post(f"/tournaments/{t['id']}/open")
    await _onboard_participants(async_client, db_session, organizer, t["id"], 6)

    resp = await async_client.post(f"/tournaments/{t['id']}/start")
    assert resp.status_code == 200

    sched = (await async_client.get(f"/tournaments/{t['id']}/schedule")).json()
    assert len(sched["rounds"]) == 1  # only round 1 generated for single-elim
    r1 = sched["rounds"][0]
    byes = [m for m in r1["matches"] if m["is_bye"]]
    assert len(byes) == 2


@pytest.mark.asyncio
async def test_tournament_detail_hidden_for_outsider_returns_404(async_client):
    organizer = await register_user(async_client, "org@example.com", "Org")
    t = (await async_client.post("/tournaments", json={"name": "T", "format": "round_robin"})).json()

    await register_user(async_client, "outsider@example.com", "Outsider")
    resp = await async_client.get(f"/tournaments/{t['id']}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_modify_by_non_organizer_forbidden(async_client):
    organizer = await register_user(async_client, "org@example.com", "Org")
    t = (await async_client.post("/tournaments", json={"name": "T", "format": "round_robin"})).json()
    outsider = await register_user(async_client, "outsider@example.com", "Outsider")
    resp = await async_client.post(f"/tournaments/{t['id']}/open")
    assert resp.status_code == 403


# --- POST /tournaments/{id}/join: organizer self-join -------------------


@pytest.mark.asyncio
async def test_organizer_with_linked_riot_can_join_own_tournament(async_client, db_session):
    from tests.helpers import link_riot

    organizer = await register_user(async_client, "org@example.com", "Org")
    await link_riot(db_session, organizer)
    created = (await async_client.post("/tournaments", json={"name": "T", "format": "round_robin"})).json()

    resp = await async_client.post(f"/tournaments/{created['id']}/join")
    assert resp.status_code == 200, resp.text
    participants = resp.json()["participants"]
    assert [p["user_id"] for p in participants] == [organizer["id"]]

    # Joining twice conflicts.
    again = await async_client.post(f"/tournaments/{created['id']}/join")
    assert again.status_code == 409


@pytest.mark.asyncio
async def test_organizer_join_requires_linked_riot_account(async_client):
    await register_user(async_client, "org@example.com", "Org")
    created = (await async_client.post("/tournaments", json={"name": "T", "format": "round_robin"})).json()

    resp = await async_client.post(f"/tournaments/{created['id']}/join")
    assert resp.status_code == 409
    assert "vincular" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_non_organizer_cannot_join_tournament(async_client, db_session):
    from tests.helpers import link_riot

    await register_user(async_client, "org@example.com", "Org")
    created = (await async_client.post("/tournaments", json={"name": "T", "format": "round_robin"})).json()

    other = await register_user(async_client, "other@example.com", "Other")
    await link_riot(db_session, other)
    resp = await async_client.post(f"/tournaments/{created['id']}/join")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_organizer_cannot_join_after_terminal_state(async_client, db_session):
    from tests.helpers import link_riot

    organizer = await register_user(async_client, "org@example.com", "Org")
    await link_riot(db_session, organizer)
    created = (await async_client.post("/tournaments", json={"name": "T", "format": "round_robin"})).json()
    await async_client.post(f"/tournaments/{created['id']}/cancel")

    resp = await async_client.post(f"/tournaments/{created['id']}/join")
    assert resp.status_code == 409
