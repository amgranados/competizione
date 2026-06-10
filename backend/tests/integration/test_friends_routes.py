"""Integration tests for /api/friends routes (004-add-friends)."""
from __future__ import annotations

import pytest

from tests.helpers import register_user, switch_user

# --- Phase 2: foundational auth ----------------------------------------


@pytest.mark.asyncio
async def test_friends_search_requires_authentication(async_client):
    async_client.cookies.clear()
    response = await async_client.get("/api/friends/search", params={"q": "foo"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_friends_requests_endpoint_requires_authentication(async_client):
    async_client.cookies.clear()
    response = await async_client.get("/api/friends/requests")
    assert response.status_code == 401


# --- Phase 3 (US1): search ---------------------------------------------


@pytest.mark.asyncio
async def test_friends_search_returns_results_with_relationship_status(async_client):
    bob = await register_user(async_client, "bob@example.com", "bob")
    alice = await register_user(async_client, "alice@example.com", "alice")
    switch_user(async_client, alice)

    response = await async_client.get("/api/friends/search", params={"q": "bob"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body) == 1
    item = body[0]
    assert item["id"] == bob["id"]
    assert item["nickname"] == "bob"
    assert item["avatar_url"] is None
    assert item["relationship_status"] == "SIN_RELACION"


@pytest.mark.asyncio
async def test_friends_search_excludes_authenticated_user(async_client):
    await register_user(async_client, "alice@example.com", "alice")
    response = await async_client.get("/api/friends/search", params={"q": "ali"})
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_friends_search_returns_empty_list_when_q_blank(async_client):
    await register_user(async_client, "alice@example.com", "alice")
    response = await async_client.get("/api/friends/search", params={"q": ""})
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_friends_search_q_too_long_returns_422(async_client):
    await register_user(async_client, "alice@example.com", "alice")
    response = await async_client.get("/api/friends/search", params={"q": "x" * 65})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_friends_search_truncates_to_20_results(async_client):
    # 25 users with `userNN` nicknames (only A-Za-z allowed, so map to letters).
    for i in range(25):
        await register_user(
            async_client, f"u{i}@example.com", f"useralpha{chr(ord('a') + (i % 26))}{i:02d}".replace("0", "z").replace("1", "y").replace("2", "w").replace("3", "v").replace("4", "t").replace("5", "s").replace("6", "r").replace("7", "q").replace("8", "p").replace("9", "o")
        )
    me = await register_user(async_client, "me@example.com", "metest")
    switch_user(async_client, me)

    response = await async_client.get("/api/friends/search", params={"q": "useralpha"})
    assert response.status_code == 200
    assert len(response.json()) == 20


@pytest.mark.asyncio
async def test_friends_search_relationship_status_reflects_pending_sent(async_client):
    bob = await register_user(async_client, "bob@example.com", "bob")
    alice = await register_user(async_client, "alice@example.com", "alice")
    switch_user(async_client, alice)

    create = await async_client.post(f"/api/friends/request/{bob['id']}")
    assert create.status_code == 201, create.text

    response = await async_client.get("/api/friends/search", params={"q": "bob"})
    assert response.status_code == 200
    assert response.json()[0]["relationship_status"] == "PENDIENTE_ENVIADA"


@pytest.mark.asyncio
async def test_friends_search_relationship_status_reflects_accepted(async_client):
    bob = await register_user(async_client, "bob@example.com", "bob")
    alice = await register_user(async_client, "alice@example.com", "alice")
    switch_user(async_client, alice)

    create = await async_client.post(f"/api/friends/request/{bob['id']}")
    request_id = create.json()["id"]

    switch_user(async_client, bob)
    accept = await async_client.post(f"/api/friends/request/{request_id}/accept")
    assert accept.status_code == 200, accept.text

    switch_user(async_client, alice)
    response = await async_client.get("/api/friends/search", params={"q": "bob"})
    assert response.status_code == 200
    assert response.json()[0]["relationship_status"] == "AMIGO"


# --- Phase 4 (US2): friendship management ------------------------------


@pytest.mark.asyncio
async def test_post_friend_request_returns_201_and_persists(async_client):
    bob = await register_user(async_client, "bob@example.com", "bob")
    alice = await register_user(async_client, "alice@example.com", "alice")
    switch_user(async_client, alice)

    response = await async_client.post(f"/api/friends/request/{bob['id']}")

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["requester_id"] == alice["id"]
    assert body["addressee_id"] == bob["id"]
    assert body["requester_nickname"] == "alice"


@pytest.mark.asyncio
async def test_post_friend_request_to_self_returns_400(async_client):
    alice = await register_user(async_client, "alice@example.com", "alice")
    response = await async_client.post(f"/api/friends/request/{alice['id']}")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_post_friend_request_to_unknown_user_returns_404(async_client):
    import uuid as uuid_mod
    await register_user(async_client, "alice@example.com", "alice")
    response = await async_client.post(f"/api/friends/request/{uuid_mod.uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_post_friend_request_returns_409_when_already_friends(async_client):
    bob = await register_user(async_client, "bob@example.com", "bob")
    alice = await register_user(async_client, "alice@example.com", "alice")
    switch_user(async_client, alice)

    create = await async_client.post(f"/api/friends/request/{bob['id']}")
    request_id = create.json()["id"]
    switch_user(async_client, bob)
    await async_client.post(f"/api/friends/request/{request_id}/accept")
    switch_user(async_client, alice)

    retry = await async_client.post(f"/api/friends/request/{bob['id']}")
    assert retry.status_code == 409
    assert "amig" in retry.json()["detail"].lower()


@pytest.mark.asyncio
async def test_post_friend_request_returns_409_when_pending_same_direction(async_client):
    bob = await register_user(async_client, "bob@example.com", "bob")
    alice = await register_user(async_client, "alice@example.com", "alice")
    switch_user(async_client, alice)

    first = await async_client.post(f"/api/friends/request/{bob['id']}")
    assert first.status_code == 201

    retry = await async_client.post(f"/api/friends/request/{bob['id']}")
    assert retry.status_code == 409


@pytest.mark.asyncio
async def test_post_friend_request_returns_409_when_pending_cross_direction(async_client):
    bob = await register_user(async_client, "bob@example.com", "bob")
    alice = await register_user(async_client, "alice@example.com", "alice")
    switch_user(async_client, alice)

    first = await async_client.post(f"/api/friends/request/{bob['id']}")
    assert first.status_code == 201

    switch_user(async_client, bob)
    cross = await async_client.post(f"/api/friends/request/{alice['id']}")
    assert cross.status_code == 409
    assert "ya te ha enviado" in cross.json()["detail"]


@pytest.mark.asyncio
async def test_post_accept_request_returns_200_and_marks_accepted(async_client):
    bob = await register_user(async_client, "bob@example.com", "bob")
    alice = await register_user(async_client, "alice@example.com", "alice")
    switch_user(async_client, alice)
    create = await async_client.post(f"/api/friends/request/{bob['id']}")
    request_id = create.json()["id"]

    switch_user(async_client, bob)
    response = await async_client.post(f"/api/friends/request/{request_id}/accept")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["action"] == "accepted"
    assert body["relationship_status"] == "AMIGO"


@pytest.mark.asyncio
async def test_post_accept_request_returns_403_when_not_addressee(async_client):
    bob = await register_user(async_client, "bob@example.com", "bob")
    alice = await register_user(async_client, "alice@example.com", "alice")
    switch_user(async_client, alice)
    create = await async_client.post(f"/api/friends/request/{bob['id']}")
    request_id = create.json()["id"]

    response = await async_client.post(f"/api/friends/request/{request_id}/accept")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_post_accept_request_returns_404_when_not_pending(async_client):
    import uuid as uuid_mod
    await register_user(async_client, "alice@example.com", "alice")
    response = await async_client.post(
        f"/api/friends/request/{uuid_mod.uuid4()}/accept"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_post_reject_request_returns_200_and_deletes_row(async_client):
    bob = await register_user(async_client, "bob@example.com", "bob")
    alice = await register_user(async_client, "alice@example.com", "alice")
    switch_user(async_client, alice)
    create = await async_client.post(f"/api/friends/request/{bob['id']}")
    request_id = create.json()["id"]

    switch_user(async_client, bob)
    response = await async_client.post(f"/api/friends/request/{request_id}/reject")
    assert response.status_code == 200
    body = response.json()
    assert body["action"] == "rejected"
    assert body["relationship_status"] == "SIN_RELACION"

    # GET inbox shows nothing
    inbox = await async_client.get("/api/friends/requests")
    assert inbox.status_code == 200
    assert inbox.json() == []


@pytest.mark.asyncio
async def test_post_reject_request_returns_403_when_not_addressee(async_client):
    bob = await register_user(async_client, "bob@example.com", "bob")
    alice = await register_user(async_client, "alice@example.com", "alice")
    switch_user(async_client, alice)
    create = await async_client.post(f"/api/friends/request/{bob['id']}")
    request_id = create.json()["id"]

    response = await async_client.post(f"/api/friends/request/{request_id}/reject")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_friend_returns_204_when_friends(async_client):
    bob = await register_user(async_client, "bob@example.com", "bob")
    alice = await register_user(async_client, "alice@example.com", "alice")
    switch_user(async_client, alice)
    create = await async_client.post(f"/api/friends/request/{bob['id']}")
    request_id = create.json()["id"]
    switch_user(async_client, bob)
    await async_client.post(f"/api/friends/request/{request_id}/accept")

    switch_user(async_client, alice)
    delete = await async_client.delete(f"/api/friends/{bob['id']}")
    assert delete.status_code == 204

    profile = await async_client.get("/api/profile/bob")
    assert profile.status_code == 200
    assert profile.json()["relationship_status"] == "SIN_RELACION"


@pytest.mark.asyncio
async def test_delete_friend_returns_204_regardless_of_who_initiated(async_client):
    bob = await register_user(async_client, "bob@example.com", "bob")
    alice = await register_user(async_client, "alice@example.com", "alice")
    switch_user(async_client, alice)
    create = await async_client.post(f"/api/friends/request/{bob['id']}")
    request_id = create.json()["id"]
    switch_user(async_client, bob)
    await async_client.post(f"/api/friends/request/{request_id}/accept")

    # bob (the addressee) deletes the friendship.
    delete = await async_client.delete(f"/api/friends/{alice['id']}")
    assert delete.status_code == 204


@pytest.mark.asyncio
async def test_delete_friend_returns_404_when_no_accepted_friendship(async_client):
    bob = await register_user(async_client, "bob@example.com", "bob")
    alice = await register_user(async_client, "alice@example.com", "alice")
    switch_user(async_client, alice)

    response = await async_client.delete(f"/api/friends/{bob['id']}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_friend_returns_404_when_only_pending_request_exists(async_client):
    bob = await register_user(async_client, "bob@example.com", "bob")
    alice = await register_user(async_client, "alice@example.com", "alice")
    switch_user(async_client, alice)
    await async_client.post(f"/api/friends/request/{bob['id']}")

    response = await async_client.delete(f"/api/friends/{bob['id']}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_friends_requests_returns_received_pending(async_client):
    bob = await register_user(async_client, "bob@example.com", "bob")
    alice = await register_user(async_client, "alice@example.com", "alice")
    switch_user(async_client, alice)
    await async_client.post(f"/api/friends/request/{bob['id']}")

    switch_user(async_client, bob)
    response = await async_client.get("/api/friends/requests")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["requester_nickname"] == "alice"


@pytest.mark.asyncio
async def test_get_friends_requests_returns_empty_for_user_without_received(async_client):
    bob = await register_user(async_client, "bob@example.com", "bob")
    alice = await register_user(async_client, "alice@example.com", "alice")
    switch_user(async_client, alice)
    await async_client.post(f"/api/friends/request/{bob['id']}")

    response = await async_client.get("/api/friends/requests")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_concurrent_cross_requests_only_one_succeeds(async_client):
    """Race-coherent simulation: alice -> bob succeeds; bob -> alice gets a
    409 with the cross-direction detail (HD-3 / INV-12)."""
    bob = await register_user(async_client, "bob@example.com", "bob")
    alice = await register_user(async_client, "alice@example.com", "alice")
    switch_user(async_client, alice)

    first = await async_client.post(f"/api/friends/request/{bob['id']}")
    assert first.status_code == 201

    switch_user(async_client, bob)
    second = await async_client.post(f"/api/friends/request/{alice['id']}")
    assert second.status_code == 409
    assert "ya te ha enviado" in second.json()["detail"]


# --- GET /api/friends: friends list ------------------------------------


@pytest.mark.asyncio
async def test_list_friends_requires_authentication(async_client):
    async_client.cookies.clear()
    response = await async_client.get("/api/friends")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_friends_returns_only_accepted_friendships(async_client):
    bob = await register_user(async_client, "bob@example.com", "bob")
    carol = await register_user(async_client, "carol@example.com", "carol")
    alice = await register_user(async_client, "alice@example.com", "alice")

    # alice -> bob accepted; alice -> carol stays pending.
    switch_user(async_client, alice)
    accepted = await async_client.post(f"/api/friends/request/{bob['id']}")
    request_id = accepted.json()["id"]
    await async_client.post(f"/api/friends/request/{carol['id']}")

    switch_user(async_client, bob)
    assert (await async_client.post(f"/api/friends/request/{request_id}/accept")).status_code == 200

    switch_user(async_client, alice)
    response = await async_client.get("/api/friends")
    assert response.status_code == 200, response.text
    body = response.json()
    assert [f["nickname"] for f in body] == ["bob"]
    assert body[0]["id"] == bob["id"]
    assert body[0]["relationship_status"] == "AMIGO"

    # The friendship is bidirectional: bob sees alice too.
    switch_user(async_client, bob)
    response = await async_client.get("/api/friends")
    assert [f["nickname"] for f in response.json()] == ["alice"]


@pytest.mark.asyncio
async def test_list_friends_empty_when_no_friends(async_client):
    await register_user(async_client, "alice@example.com", "alice")
    response = await async_client.get("/api/friends")
    assert response.status_code == 200
    assert response.json() == []
