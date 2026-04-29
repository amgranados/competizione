"""Friends service — search users, manage friendship requests and
relationships, and compute the relationship status as seen by the
authenticated user (004-add-friends).

The relationship is stored as a single row per pair (HD-2): a `pending` row
represents a directional request, an `accepted` row represents a
bidirectional friendship. The cross-direction race is handled with
`SELECT ... FOR UPDATE` inside a transaction (HD-3).
"""
from __future__ import annotations

import uuid
from typing import Iterable, Mapping

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.friendship import Friendship
from app.models.riot_account import RiotAccount
from app.models.user import User
from app.schemas.friends import (
    FriendRequestActionResult,
    FriendRequestResponse,
    FriendshipStatus,
    UserSearchResult,
)
from app.schemas.notification import NotificationType
from app.services import notification_service


# --- Domain exceptions ----------------------------------------------------


class UserNotFound(Exception):
    """Target user does not exist or has been anonymized (HD-5)."""


class SelfFriendRequest(Exception):
    """Tried to send a friend request to oneself (FR-014)."""


class FriendshipAlreadyExists(Exception):
    """A relationship row already exists in some state (HD-3).

    `kind` distinguishes the case so the route layer can return a precise
    detail message:
    - "accepted": already friends.
    - "pending_sent": current user already sent a pending request.
    - "pending_received": the target already sent a pending request to us.
    """

    def __init__(self, kind: str) -> None:
        super().__init__(kind)
        self.kind = kind


class RequestNotFound(Exception):
    """Pending request does not exist or is no longer pending."""


class NotRequestAddressee(Exception):
    """The authenticated user is not the addressee of the request."""


class FriendshipNotFound(Exception):
    """No accepted friendship row exists between the two users."""


class NotRequestRequester(Exception):
    """Tried to cancel a pending request the user did not send."""


# --- Helpers --------------------------------------------------------------


def _pair_filter(a: uuid.UUID, b: uuid.UUID):
    """SQL predicate matching a friendship row in either direction."""
    return or_(
        and_(Friendship.requester_id == a, Friendship.addressee_id == b),
        and_(Friendship.requester_id == b, Friendship.addressee_id == a),
    )


# --- Read APIs ------------------------------------------------------------


async def compute_relationship_status(
    session: AsyncSession,
    current_user_id: uuid.UUID,
    target_user_id: uuid.UUID,
) -> FriendshipStatus:
    """Return the FriendshipStatus between current and target user (HD-1).

    A single SELECT with OR over both directions, LIMIT 1.
    """
    status, _ = await compute_relationship_state(
        session, current_user_id, target_user_id
    )
    return status


async def compute_relationship_state(
    session: AsyncSession,
    current_user_id: uuid.UUID,
    target_user_id: uuid.UUID,
) -> tuple[FriendshipStatus, uuid.UUID | None]:
    """Like `compute_relationship_status` but also returns the friendship row
    id when one exists. The id is useful to accept/reject inline (HD-1).
    """
    if current_user_id == target_user_id:
        return FriendshipStatus.SIN_RELACION, None

    stmt = (
        select(
            Friendship.id,
            Friendship.requester_id,
            Friendship.addressee_id,
            Friendship.status,
        )
        .where(_pair_filter(current_user_id, target_user_id))
        .limit(1)
    )
    row = (await session.execute(stmt)).first()
    if row is None:
        return FriendshipStatus.SIN_RELACION, None

    friendship_id, requester_id, _, status = row
    if status == "accepted":
        return FriendshipStatus.AMIGO, None
    # pending
    if requester_id == current_user_id:
        return FriendshipStatus.PENDIENTE_ENVIADA, friendship_id
    return FriendshipStatus.PENDIENTE_RECIBIDA, friendship_id


async def _bulk_relationship_state(
    session: AsyncSession,
    current_user_id: uuid.UUID,
    target_ids: Iterable[uuid.UUID],
) -> Mapping[uuid.UUID, tuple[FriendshipStatus, uuid.UUID | None]]:
    """Compute (relationship_status, pending_request_id) for multiple targets
    in a single query (avoids N+1 in search results).
    """
    target_list = list(target_ids)
    if not target_list:
        return {}

    stmt = select(
        Friendship.id,
        Friendship.requester_id,
        Friendship.addressee_id,
        Friendship.status,
    ).where(
        or_(
            and_(
                Friendship.requester_id == current_user_id,
                Friendship.addressee_id.in_(target_list),
            ),
            and_(
                Friendship.addressee_id == current_user_id,
                Friendship.requester_id.in_(target_list),
            ),
        )
    )
    result: dict[uuid.UUID, tuple[FriendshipStatus, uuid.UUID | None]] = {
        tid: (FriendshipStatus.SIN_RELACION, None) for tid in target_list
    }
    for friendship_id, requester_id, addressee_id, status in (await session.execute(stmt)).all():
        other = addressee_id if requester_id == current_user_id else requester_id
        if status == "accepted":
            result[other] = (FriendshipStatus.AMIGO, None)
        elif requester_id == current_user_id:
            result[other] = (FriendshipStatus.PENDIENTE_ENVIADA, friendship_id)
        else:
            result[other] = (FriendshipStatus.PENDIENTE_RECIBIDA, friendship_id)
    return result


_SEARCH_LIMIT = 20


async def search_users(
    session: AsyncSession,
    current_user_id: uuid.UUID,
    q: str,
) -> list[UserSearchResult]:
    """Return up to 20 users whose nickname matches `%q%` (case-insensitive),
    excluding the authenticated user and anonymized users (HD-5, HD-6).
    """
    q_clean = (q or "").strip()
    if not q_clean:
        return []

    pattern = f"%{q_clean}%"
    stmt = (
        select(User)
        .where(
            User.nickname.ilike(pattern),
            User.id != current_user_id,
            User.deleted_at.is_(None),
        )
        .order_by(User.nickname.asc())
        .limit(_SEARCH_LIMIT)
    )
    users = (await session.execute(stmt)).scalars().all()
    if not users:
        return []

    states = await _bulk_relationship_state(
        session, current_user_id, [u.id for u in users]
    )
    return [
        UserSearchResult(
            id=u.id,
            nickname=u.nickname,
            avatar_url=u.avatar_url,
            relationship_status=states[u.id][0],
            pending_request_id=states[u.id][1],
        )
        for u in users
    ]


# --- Write APIs (US2) -----------------------------------------------------


async def send_request(
    session: AsyncSession,
    *,
    requester_id: uuid.UUID,
    addressee_id: uuid.UUID,
) -> FriendRequestResponse:
    """Create a `pending` friendship row from `requester_id` to `addressee_id`.

    Race-safe (HD-3): runs `SELECT ... FOR UPDATE` over both directions inside
    the transaction, so a simultaneous A->B and B->A submission ends with one
    `pending` row and one `409 (FriendshipAlreadyExists)`. The UNIQUE
    constraint on `(requester_id, addressee_id)` is the second line of
    defense.
    """
    if requester_id == addressee_id:
        raise SelfFriendRequest

    addressee = await session.get(User, addressee_id)
    if addressee is None or addressee.deleted_at is not None:
        raise UserNotFound

    requester = await session.get(User, requester_id)
    if requester is None:  # should not happen given auth dependency
        raise UserNotFound

    # Try to take a row-level lock. SQLite (used in tests) ignores `for_update`
    # gracefully; PostgreSQL applies the lock as expected.
    lock_stmt = (
        select(Friendship)
        .where(_pair_filter(requester_id, addressee_id))
        .with_for_update()
    )
    existing = (await session.execute(lock_stmt)).scalar_one_or_none()
    if existing is not None:
        if existing.status == "accepted":
            raise FriendshipAlreadyExists("accepted")
        if existing.requester_id == requester_id:
            raise FriendshipAlreadyExists("pending_sent")
        raise FriendshipAlreadyExists("pending_received")

    friendship = Friendship(
        requester_id=requester_id,
        addressee_id=addressee_id,
        status="pending",
    )
    session.add(friendship)
    try:
        await session.flush()
        await notification_service.create_notification(
            session,
            user_id=addressee_id,
            type=NotificationType.FRIEND_REQUEST_RECEIVED.value,
            friendship_id=friendship.id,
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        # Race winner committed between our SELECT and INSERT.
        raise FriendshipAlreadyExists("pending_sent") from exc

    await session.refresh(friendship)
    return FriendRequestResponse(
        id=friendship.id,
        requester_id=friendship.requester_id,
        addressee_id=friendship.addressee_id,
        requester_nickname=requester.nickname,
        requester_avatar_url=requester.avatar_url,
        created_at=friendship.created_at,
    )


async def _load_pending_for_addressee(
    session: AsyncSession,
    request_id: uuid.UUID,
    current_user_id: uuid.UUID,
) -> Friendship:
    """Load the pending row by id, raising if missing / not pending / addressee
    mismatch / requester anonymized."""
    friendship = await session.get(Friendship, request_id)
    if friendship is None or friendship.status != "pending":
        raise RequestNotFound
    if friendship.addressee_id != current_user_id:
        raise NotRequestAddressee

    requester = await session.get(User, friendship.requester_id)
    if requester is None or requester.deleted_at is not None:
        raise RequestNotFound
    return friendship


async def accept_request(
    session: AsyncSession,
    request_id: uuid.UUID,
    current_user_id: uuid.UUID,
) -> FriendRequestActionResult:
    """Mark a pending request as accepted (HD-2: UPDATE, not INSERT). Also
    notify the original requester that the friendship was accepted."""
    friendship = await _load_pending_for_addressee(session, request_id, current_user_id)
    friendship.status = "accepted"
    await notification_service.create_notification(
        session,
        user_id=friendship.requester_id,
        type=NotificationType.FRIEND_REQUEST_ACCEPTED.value,
        friendship_id=friendship.id,
    )
    await session.commit()
    return FriendRequestActionResult(
        request_id=friendship.id,
        action="accepted",
        relationship_status=FriendshipStatus.AMIGO,
    )


async def reject_request(
    session: AsyncSession,
    request_id: uuid.UUID,
    current_user_id: uuid.UUID,
) -> FriendRequestActionResult:
    """Reject a pending request — DELETE the row so the requester can re-send
    later (consistent with the spec assumption)."""
    friendship = await _load_pending_for_addressee(session, request_id, current_user_id)
    request_id_value = friendship.id
    await session.delete(friendship)
    await session.commit()
    return FriendRequestActionResult(
        request_id=request_id_value,
        action="rejected",
        relationship_status=FriendshipStatus.SIN_RELACION,
    )


async def remove_friend(
    session: AsyncSession,
    *,
    current_user_id: uuid.UUID,
    target_user_id: uuid.UUID,
) -> None:
    """Delete the single `accepted` row that links the two users (HD-4).

    Bidirectional by design: a single row represents the friendship, so one
    DELETE removes it for both sides.
    """
    stmt = (
        select(Friendship)
        .where(
            _pair_filter(current_user_id, target_user_id),
            Friendship.status == "accepted",
        )
        .limit(1)
    )
    friendship = (await session.execute(stmt)).scalar_one_or_none()
    if friendship is None:
        raise FriendshipNotFound
    await session.delete(friendship)
    await session.commit()


async def cancel_request(
    session: AsyncSession,
    request_id: uuid.UUID,
    current_user_id: uuid.UUID,
) -> None:
    """Cancel a pending request previously sent by the current user.

    Only the requester can cancel; the addressee uses accept/reject. Deletes
    the row so the requester can re-send later if they want.
    """
    friendship = await session.get(Friendship, request_id)
    if friendship is None or friendship.status != "pending":
        raise RequestNotFound
    if friendship.requester_id != current_user_id:
        raise NotRequestRequester
    await session.delete(friendship)
    await session.commit()


async def list_invitable_friends(
    session: AsyncSession,
    current_user_id: uuid.UUID,
) -> list[UserSearchResult]:
    """Friends (accepted friendships) of the current user that have a linked
    LoL account. Used by tournament creation/invitation flows: only such
    friends can be invited to a tournament.

    Returns the same shape as `search_users` for UI reuse.
    """
    stmt = (
        select(User, Friendship)
        .join(
            Friendship,
            or_(
                and_(
                    Friendship.requester_id == current_user_id,
                    Friendship.addressee_id == User.id,
                ),
                and_(
                    Friendship.addressee_id == current_user_id,
                    Friendship.requester_id == User.id,
                ),
            ),
        )
        .join(RiotAccount, RiotAccount.user_id == User.id)
        .where(
            Friendship.status == "accepted",
            User.deleted_at.is_(None),
            User.id != current_user_id,
        )
        .order_by(User.nickname.asc())
    )
    rows = (await session.execute(stmt)).all()
    return [
        UserSearchResult(
            id=user.id,
            nickname=user.nickname,
            avatar_url=user.avatar_url,
            relationship_status=FriendshipStatus.AMIGO,
            pending_request_id=None,
        )
        for user, _ in rows
    ]


async def list_received_requests(
    session: AsyncSession,
    current_user_id: uuid.UUID,
) -> list[FriendRequestResponse]:
    """Pending requests where the authenticated user is the addressee.

    Filters out anonymized requesters (HD-5).
    """
    stmt = (
        select(Friendship, User)
        .join(User, User.id == Friendship.requester_id)
        .where(
            Friendship.addressee_id == current_user_id,
            Friendship.status == "pending",
            User.deleted_at.is_(None),
        )
        .order_by(Friendship.created_at.desc())
    )
    rows = (await session.execute(stmt)).all()
    return [
        FriendRequestResponse(
            id=fr.id,
            requester_id=fr.requester_id,
            addressee_id=fr.addressee_id,
            requester_nickname=requester.nickname,
            requester_avatar_url=requester.avatar_url,
            created_at=fr.created_at,
        )
        for fr, requester in rows
    ]
