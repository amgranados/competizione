"""Unit tests for friends_service (004-add-friends)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.friendship import Friendship
from app.models.user import User
from app.schemas.friends import FriendshipStatus
from app.services import friends_service

# --- Helpers -------------------------------------------------------------


async def _create_user(
    session, *, nickname: str, email: str | None = None, deleted: bool = False
) -> User:
    user = User(
        email=email or f"{nickname}@example.com",
        nickname=nickname,
        password_hash="!hash",
    )
    if deleted:
        user.deleted_at = datetime.now(timezone.utc)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _create_friendship(session, requester: User, addressee: User, status: str) -> Friendship:
    friendship = Friendship(
        requester_id=requester.id,
        addressee_id=addressee.id,
        status=status,
    )
    session.add(friendship)
    await session.commit()
    await session.refresh(friendship)
    return friendship


# --- Foundational: model & enum -----------------------------------------


@pytest.mark.asyncio
async def test_friendship_unique_per_direction(db_session):
    alice = await _create_user(db_session, nickname="alice")
    bob = await _create_user(db_session, nickname="bob")

    db_session.add(Friendship(requester_id=alice.id, addressee_id=bob.id, status="pending"))
    await db_session.commit()

    db_session.add(Friendship(requester_id=alice.id, addressee_id=bob.id, status="pending"))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_friendship_check_no_self_link(db_session):
    alice = await _create_user(db_session, nickname="alice")

    db_session.add(Friendship(requester_id=alice.id, addressee_id=alice.id, status="pending"))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_friendship_status_enum_values(db_session):
    alice = await _create_user(db_session, nickname="alice")
    bob = await _create_user(db_session, nickname="bob")
    carl = await _create_user(db_session, nickname="carl")

    db_session.add(Friendship(requester_id=alice.id, addressee_id=bob.id, status="pending"))
    db_session.add(Friendship(requester_id=alice.id, addressee_id=carl.id, status="accepted"))
    await db_session.commit()

    db_session.add(Friendship(requester_id=bob.id, addressee_id=carl.id, status="garbage"))
    with pytest.raises(Exception):
        await db_session.commit()
    await db_session.rollback()


# --- compute_relationship_status ----------------------------------------


@pytest.mark.asyncio
async def test_compute_relationship_status_when_no_relation(db_session):
    alice = await _create_user(db_session, nickname="alice")
    bob = await _create_user(db_session, nickname="bob")

    status = await friends_service.compute_relationship_status(db_session, alice.id, bob.id)
    assert status == FriendshipStatus.SIN_RELACION


@pytest.mark.asyncio
async def test_compute_relationship_status_when_pending_sent(db_session):
    alice = await _create_user(db_session, nickname="alice")
    bob = await _create_user(db_session, nickname="bob")
    await _create_friendship(db_session, alice, bob, "pending")

    assert (
        await friends_service.compute_relationship_status(db_session, alice.id, bob.id)
        == FriendshipStatus.PENDIENTE_ENVIADA
    )
    assert (
        await friends_service.compute_relationship_status(db_session, bob.id, alice.id)
        == FriendshipStatus.PENDIENTE_RECIBIDA
    )


@pytest.mark.asyncio
async def test_compute_relationship_status_when_accepted(db_session):
    alice = await _create_user(db_session, nickname="alice")
    bob = await _create_user(db_session, nickname="bob")
    await _create_friendship(db_session, alice, bob, "accepted")

    assert (
        await friends_service.compute_relationship_status(db_session, alice.id, bob.id)
        == FriendshipStatus.AMIGO
    )
    assert (
        await friends_service.compute_relationship_status(db_session, bob.id, alice.id)
        == FriendshipStatus.AMIGO
    )


# --- search_users (US1) -------------------------------------------------


@pytest.mark.asyncio
async def test_search_returns_empty_list_for_blank_query(db_session):
    alice = await _create_user(db_session, nickname="alice")
    await _create_user(db_session, nickname="bob")

    assert await friends_service.search_users(db_session, alice.id, "") == []
    assert await friends_service.search_users(db_session, alice.id, "   ") == []


@pytest.mark.asyncio
async def test_search_is_case_insensitive(db_session):
    alice = await _create_user(db_session, nickname="alice")
    await _create_user(db_session, nickname="Bob")
    await _create_user(db_session, nickname="BOBBY")

    upper = await friends_service.search_users(db_session, alice.id, "BOB")
    lower = await friends_service.search_users(db_session, alice.id, "bob")
    assert {u.nickname for u in upper} == {"Bob", "BOBBY"}
    assert {u.nickname for u in lower} == {"Bob", "BOBBY"}


@pytest.mark.asyncio
async def test_search_partial_match_inside_nickname(db_session):
    carl = await _create_user(db_session, nickname="carl")
    await _create_user(db_session, nickname="xbobx")
    await _create_user(db_session, nickname="bobby")
    await _create_user(db_session, nickname="john")

    res = await friends_service.search_users(db_session, carl.id, "bob")
    assert {u.nickname for u in res} == {"xbobx", "bobby"}


@pytest.mark.asyncio
async def test_search_limited_to_20_results(db_session):
    me = await _create_user(db_session, nickname="me")
    for i in range(25):
        await _create_user(db_session, nickname=f"user{i:02d}")

    res = await friends_service.search_users(db_session, me.id, "user")
    assert len(res) == 20


@pytest.mark.asyncio
async def test_search_excludes_self(db_session):
    alice = await _create_user(db_session, nickname="alice")
    await _create_user(db_session, nickname="alicia")

    res = await friends_service.search_users(db_session, alice.id, "ali")
    nicknames = {u.nickname for u in res}
    assert "alice" not in nicknames
    assert "alicia" in nicknames


@pytest.mark.asyncio
async def test_search_excludes_anonymized_users(db_session):
    alice = await _create_user(db_session, nickname="alice")
    await _create_user(db_session, nickname="deleted-AAAAAAAA", deleted=True)
    await _create_user(db_session, nickname="bob")

    res = await friends_service.search_users(db_session, alice.id, "delet")
    assert res == []


@pytest.mark.asyncio
async def test_search_results_include_relationship_status_per_row(db_session):
    me = await _create_user(db_session, nickname="me")
    no_relation = await _create_user(db_session, nickname="user_none")
    pending_target = await _create_user(db_session, nickname="user_pending")
    friend = await _create_user(db_session, nickname="user_friend")

    await _create_friendship(db_session, me, pending_target, "pending")
    await _create_friendship(db_session, me, friend, "accepted")

    res = await friends_service.search_users(db_session, me.id, "user_")
    by_id = {r.id: r for r in res}
    assert by_id[no_relation.id].relationship_status == FriendshipStatus.SIN_RELACION
    assert by_id[pending_target.id].relationship_status == FriendshipStatus.PENDIENTE_ENVIADA
    assert by_id[friend.id].relationship_status == FriendshipStatus.AMIGO


# --- send_request (US2) -------------------------------------------------


@pytest.mark.asyncio
async def test_send_request_creates_pending_row(db_session):
    alice = await _create_user(db_session, nickname="alice")
    bob = await _create_user(db_session, nickname="bob")

    response = await friends_service.send_request(
        db_session, requester_id=alice.id, addressee_id=bob.id
    )
    assert response.requester_id == alice.id
    assert response.addressee_id == bob.id

    from sqlalchemy import select as _select
    rows = (await db_session.execute(_select(Friendship))).scalars().all()
    assert len(rows) == 1
    assert rows[0].status == "pending"


@pytest.mark.asyncio
async def test_send_request_to_self_raises_self_friend_request(db_session):
    alice = await _create_user(db_session, nickname="alice")
    with pytest.raises(friends_service.SelfFriendRequest):
        await friends_service.send_request(
            db_session, requester_id=alice.id, addressee_id=alice.id
        )


@pytest.mark.asyncio
async def test_send_request_to_unknown_user_raises_not_found(db_session):
    import uuid
    alice = await _create_user(db_session, nickname="alice")
    with pytest.raises(friends_service.UserNotFound):
        await friends_service.send_request(
            db_session, requester_id=alice.id, addressee_id=uuid.uuid4()
        )


@pytest.mark.asyncio
async def test_send_request_to_anonymized_user_raises_not_found(db_session):
    alice = await _create_user(db_session, nickname="alice")
    deleted = await _create_user(
        db_session, nickname="deleted-AAAAAAAA", deleted=True
    )
    with pytest.raises(friends_service.UserNotFound):
        await friends_service.send_request(
            db_session, requester_id=alice.id, addressee_id=deleted.id
        )


@pytest.mark.asyncio
async def test_send_request_rejected_when_already_friends(db_session):
    alice = await _create_user(db_session, nickname="alice")
    bob = await _create_user(db_session, nickname="bob")
    await _create_friendship(db_session, alice, bob, "accepted")

    with pytest.raises(friends_service.FriendshipAlreadyExists) as exc:
        await friends_service.send_request(
            db_session, requester_id=alice.id, addressee_id=bob.id
        )
    assert exc.value.kind == "accepted"


@pytest.mark.asyncio
async def test_send_request_rejected_when_pending_in_same_direction(db_session):
    alice = await _create_user(db_session, nickname="alice")
    bob = await _create_user(db_session, nickname="bob")
    await _create_friendship(db_session, alice, bob, "pending")

    with pytest.raises(friends_service.FriendshipAlreadyExists) as exc:
        await friends_service.send_request(
            db_session, requester_id=alice.id, addressee_id=bob.id
        )
    assert exc.value.kind == "pending_sent"


@pytest.mark.asyncio
async def test_send_request_rejected_when_pending_in_other_direction(db_session):
    alice = await _create_user(db_session, nickname="alice")
    bob = await _create_user(db_session, nickname="bob")
    await _create_friendship(db_session, alice, bob, "pending")

    with pytest.raises(friends_service.FriendshipAlreadyExists) as exc:
        await friends_service.send_request(
            db_session, requester_id=bob.id, addressee_id=alice.id
        )
    assert exc.value.kind == "pending_received"


# --- accept_request -----------------------------------------------------


@pytest.mark.asyncio
async def test_accept_request_updates_status_to_accepted(db_session):
    alice = await _create_user(db_session, nickname="alice")
    bob = await _create_user(db_session, nickname="bob")
    fr = await _create_friendship(db_session, alice, bob, "pending")

    result = await friends_service.accept_request(db_session, fr.id, bob.id)
    assert result.action == "accepted"
    assert result.relationship_status == FriendshipStatus.AMIGO

    await db_session.refresh(fr)
    assert fr.status == "accepted"


@pytest.mark.asyncio
async def test_accept_request_forbidden_for_non_addressee(db_session):
    alice = await _create_user(db_session, nickname="alice")
    bob = await _create_user(db_session, nickname="bob")
    fr = await _create_friendship(db_session, alice, bob, "pending")

    with pytest.raises(friends_service.NotRequestAddressee):
        await friends_service.accept_request(db_session, fr.id, alice.id)


@pytest.mark.asyncio
async def test_accept_request_not_found_when_already_accepted(db_session):
    alice = await _create_user(db_session, nickname="alice")
    bob = await _create_user(db_session, nickname="bob")
    fr = await _create_friendship(db_session, alice, bob, "accepted")

    with pytest.raises(friends_service.RequestNotFound):
        await friends_service.accept_request(db_session, fr.id, bob.id)


@pytest.mark.asyncio
async def test_accept_request_not_found_when_requester_anonymized(db_session):
    alice = await _create_user(db_session, nickname="alice")
    bob = await _create_user(db_session, nickname="bob")
    fr = await _create_friendship(db_session, alice, bob, "pending")

    # Anonymize alice
    from datetime import datetime, timezone
    alice.deleted_at = datetime.now(timezone.utc)
    await db_session.commit()

    with pytest.raises(friends_service.RequestNotFound):
        await friends_service.accept_request(db_session, fr.id, bob.id)


# --- reject_request -----------------------------------------------------


@pytest.mark.asyncio
async def test_reject_request_deletes_row(db_session):
    alice = await _create_user(db_session, nickname="alice")
    bob = await _create_user(db_session, nickname="bob")
    fr = await _create_friendship(db_session, alice, bob, "pending")

    result = await friends_service.reject_request(db_session, fr.id, bob.id)
    assert result.action == "rejected"
    assert result.relationship_status == FriendshipStatus.SIN_RELACION

    from sqlalchemy import select as _select
    rows = (await db_session.execute(_select(Friendship))).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_reject_request_forbidden_for_non_addressee(db_session):
    alice = await _create_user(db_session, nickname="alice")
    bob = await _create_user(db_session, nickname="bob")
    fr = await _create_friendship(db_session, alice, bob, "pending")

    with pytest.raises(friends_service.NotRequestAddressee):
        await friends_service.reject_request(db_session, fr.id, alice.id)


# --- cancel_request -----------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_request_deletes_row_when_called_by_requester(db_session):
    alice = await _create_user(db_session, nickname="alice")
    bob = await _create_user(db_session, nickname="bob")
    fr = await _create_friendship(db_session, alice, bob, "pending")

    await friends_service.cancel_request(db_session, fr.id, alice.id)

    from sqlalchemy import select as _select
    rows = (await db_session.execute(_select(Friendship))).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_cancel_request_forbidden_for_non_requester(db_session):
    alice = await _create_user(db_session, nickname="alice")
    bob = await _create_user(db_session, nickname="bob")
    fr = await _create_friendship(db_session, alice, bob, "pending")

    with pytest.raises(friends_service.NotRequestRequester):
        await friends_service.cancel_request(db_session, fr.id, bob.id)


# --- remove_friend ------------------------------------------------------


@pytest.mark.asyncio
async def test_remove_friend_deletes_single_row_regardless_of_direction(db_session):
    alice = await _create_user(db_session, nickname="alice")
    bob = await _create_user(db_session, nickname="bob")
    await _create_friendship(db_session, alice, bob, "accepted")

    # bob (addressee) removes the friendship initiated by alice
    await friends_service.remove_friend(
        db_session, current_user_id=bob.id, target_user_id=alice.id
    )
    from sqlalchemy import select as _select
    rows = (await db_session.execute(_select(Friendship))).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_remove_friend_404_when_no_accepted_friendship(db_session):
    alice = await _create_user(db_session, nickname="alice")
    bob = await _create_user(db_session, nickname="bob")
    with pytest.raises(friends_service.FriendshipNotFound):
        await friends_service.remove_friend(
            db_session, current_user_id=alice.id, target_user_id=bob.id
        )


@pytest.mark.asyncio
async def test_remove_friend_does_not_delete_pending_request(db_session):
    alice = await _create_user(db_session, nickname="alice")
    bob = await _create_user(db_session, nickname="bob")
    fr = await _create_friendship(db_session, alice, bob, "pending")

    with pytest.raises(friends_service.FriendshipNotFound):
        await friends_service.remove_friend(
            db_session, current_user_id=alice.id, target_user_id=bob.id
        )

    await db_session.refresh(fr)
    assert fr.status == "pending"


# --- list_received_requests ---------------------------------------------


@pytest.mark.asyncio
async def test_list_received_requests_returns_pending_only_for_current_user(db_session):
    alice = await _create_user(db_session, nickname="alice")
    bob = await _create_user(db_session, nickname="bob")
    carl = await _create_user(db_session, nickname="carl")
    await _create_friendship(db_session, alice, bob, "pending")
    # Unrelated friendship
    await _create_friendship(db_session, alice, carl, "accepted")

    bob_inbox = await friends_service.list_received_requests(db_session, bob.id)
    assert len(bob_inbox) == 1
    assert bob_inbox[0].requester_nickname == "alice"

    alice_inbox = await friends_service.list_received_requests(db_session, alice.id)
    assert alice_inbox == []


@pytest.mark.asyncio
async def test_list_received_requests_filters_anonymized_requesters(db_session):
    alice = await _create_user(db_session, nickname="alice")
    bob = await _create_user(db_session, nickname="bob")
    await _create_friendship(db_session, alice, bob, "pending")

    from datetime import datetime, timezone
    alice.deleted_at = datetime.now(timezone.utc)
    await db_session.commit()

    inbox = await friends_service.list_received_requests(db_session, bob.id)
    assert inbox == []
