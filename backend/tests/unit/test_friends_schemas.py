"""Unit tests for friends Pydantic schemas (004-add-friends)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.friends import (
    FriendRequestActionResult,
    FriendRequestResponse,
    FriendshipStatus,
    UserSearchResult,
)


def test_friendship_status_enum_serialization():
    assert FriendshipStatus.SIN_RELACION.value == "SIN_RELACION"
    assert FriendshipStatus.PENDIENTE_ENVIADA.value == "PENDIENTE_ENVIADA"
    assert FriendshipStatus.PENDIENTE_RECIBIDA.value == "PENDIENTE_RECIBIDA"
    assert FriendshipStatus.AMIGO.value == "AMIGO"
    # Pydantic accepts the enum value
    UserSearchResult(
        id=uuid.uuid4(),
        nickname="bob",
        avatar_url=None,
        relationship_status="AMIGO",
    )
    with pytest.raises(ValidationError):
        UserSearchResult(
            id=uuid.uuid4(),
            nickname="bob",
            avatar_url=None,
            relationship_status="UNKNOWN",
        )


def test_user_search_result_includes_relationship_status():
    payload = {
        "id": uuid.uuid4(),
        "nickname": "bob",
        "avatar_url": None,
        "relationship_status": FriendshipStatus.SIN_RELACION,
    }
    result = UserSearchResult(**payload)
    assert result.nickname == "bob"
    assert result.relationship_status == FriendshipStatus.SIN_RELACION

    with pytest.raises(ValidationError):
        UserSearchResult(
            id=uuid.uuid4(),
            nickname="bob",
            avatar_url=None,
            # missing relationship_status
        )


def test_friend_request_response_shape():
    now = datetime.now(timezone.utc)
    payload = {
        "id": uuid.uuid4(),
        "requester_id": uuid.uuid4(),
        "addressee_id": uuid.uuid4(),
        "requester_nickname": "alice",
        "requester_avatar_url": None,
        "created_at": now,
    }
    resp = FriendRequestResponse(**payload)
    assert resp.requester_nickname == "alice"
    assert resp.created_at == now

    with pytest.raises(ValidationError):
        FriendRequestResponse(
            id=uuid.uuid4(),
            requester_id=uuid.uuid4(),
            # missing addressee_id, requester_nickname, created_at
        )


def test_friend_request_action_result_enum_action():
    accepted = FriendRequestActionResult(
        request_id=uuid.uuid4(),
        action="accepted",
        relationship_status=FriendshipStatus.AMIGO,
    )
    assert accepted.action == "accepted"

    rejected = FriendRequestActionResult(
        request_id=uuid.uuid4(),
        action="rejected",
        relationship_status=FriendshipStatus.SIN_RELACION,
    )
    assert rejected.action == "rejected"

    with pytest.raises(ValidationError):
        FriendRequestActionResult(
            request_id=uuid.uuid4(),
            action="dismissed",
            relationship_status=FriendshipStatus.SIN_RELACION,
        )
