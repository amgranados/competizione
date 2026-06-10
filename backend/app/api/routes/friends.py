"""HTTP routes for /api/friends (004-add-friends)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_current_user
from app.db.base import get_db
from app.models.user import User
from app.schemas.friends import (
    FriendRequestActionResult,
    FriendRequestResponse,
    UserSearchResult,
)
from app.services import friends_service

router = APIRouter(prefix="/api/friends", tags=["friends"])


_CONFLICT_DETAILS = {
    "accepted": "Ya sois amigos.",
    "pending_sent": "Ya tienes una solicitud pendiente con este usuario.",
    "pending_received": "Este usuario ya te ha enviado una solicitud; acéptala desde tu panel.",
}


@router.get("", response_model=list[UserSearchResult])
async def list_friends(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[UserSearchResult]:
    """All accepted friends of the authenticated user."""
    return await friends_service.list_friends(session, current_user.id)


@router.get("/search", response_model=list[UserSearchResult])
async def search(
    q: str = Query(default="", max_length=64),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[UserSearchResult]:
    return await friends_service.search_users(session, current_user.id, q)


@router.get("/requests", response_model=list[FriendRequestResponse])
async def list_requests(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[FriendRequestResponse]:
    return await friends_service.list_received_requests(session, current_user.id)


@router.get("/invitable", response_model=list[UserSearchResult])
async def list_invitable(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[UserSearchResult]:
    """Friends with a linked LoL account that can be invited to a tournament."""
    return await friends_service.list_invitable_friends(session, current_user.id)


@router.post(
    "/request/{user_id}",
    response_model=FriendRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_request(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> FriendRequestResponse:
    try:
        return await friends_service.send_request(
            session,
            requester_id=current_user.id,
            addressee_id=user_id,
        )
    except friends_service.SelfFriendRequest:
        raise HTTPException(
            status_code=400,
            detail="No puedes enviarte una solicitud a ti mismo.",
        )
    except friends_service.UserNotFound:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    except friends_service.FriendshipAlreadyExists as exc:
        raise HTTPException(
            status_code=409,
            detail=_CONFLICT_DETAILS.get(exc.kind, "Ya existe una relación con este usuario."),
        )


@router.post(
    "/request/{request_id}/accept",
    response_model=FriendRequestActionResult,
)
async def post_accept(
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> FriendRequestActionResult:
    try:
        return await friends_service.accept_request(session, request_id, current_user.id)
    except friends_service.RequestNotFound:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada.")
    except friends_service.NotRequestAddressee:
        raise HTTPException(
            status_code=403,
            detail="No puedes aceptar una solicitud que no es tuya.",
        )


@router.post(
    "/request/{request_id}/reject",
    response_model=FriendRequestActionResult,
)
async def post_reject(
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> FriendRequestActionResult:
    try:
        return await friends_service.reject_request(session, request_id, current_user.id)
    except friends_service.RequestNotFound:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada.")
    except friends_service.NotRequestAddressee:
        raise HTTPException(
            status_code=403,
            detail="No puedes rechazar una solicitud que no es tuya.",
        )


@router.delete(
    "/request/{request_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def cancel_request(
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Cancel a pending request previously sent by the current user."""
    try:
        await friends_service.cancel_request(session, request_id, current_user.id)
    except friends_service.RequestNotFound:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada.")
    except friends_service.NotRequestRequester:
        raise HTTPException(
            status_code=403,
            detail="Solo puedes cancelar solicitudes que tú has enviado.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_friend(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    try:
        await friends_service.remove_friend(
            session,
            current_user_id=current_user.id,
            target_user_id=user_id,
        )
    except friends_service.FriendshipNotFound:
        raise HTTPException(status_code=404, detail="No sois amigos.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
