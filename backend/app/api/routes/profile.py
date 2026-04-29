"""HTTP routes for /api/profile (003-edit-profile)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_current_user, set_auth_cookies
from app.core import security
from app.core.config import get_settings
from app.db.base import get_db
from app.models.user import User
from app.schemas.friends import PublicProfileResponse
from app.schemas.profile import (
    DeleteAccountConfirm,
    LinkedGameSummary,
    LinkRiotAccount,
    ProfileBasic,
    ProfileResponse,
    UpdateAvatar,
    UpdateNickname,
    UpdatePassword,
)
from app.services import profile_service
from app.services.riot_api.client import get_riot_api_client

router = APIRouter(prefix="/api/profile", tags=["profile"])


def get_riot_client():
    """FastAPI dependency: returns the Riot client based on env settings.

    Tests override this via `app.dependency_overrides[get_riot_client]` to
    inject a `MockRiotAPIClient` populated with seeded fixtures.
    """
    return get_riot_api_client(get_settings())


def _basic_from_user(user: User) -> ProfileBasic:
    return ProfileBasic(
        id=user.id,
        nickname=user.nickname,
        email=user.email,
        avatar_url=user.avatar_url,
        linked_games=[],
    )


@router.get("", response_model=ProfileResponse, response_model_exclude_none=False)
async def get_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    riot_client=Depends(get_riot_client),
) -> ProfileResponse:
    try:
        return await profile_service.get_profile(
            session, current_user.id, riot_client=riot_client
        )
    except profile_service.UserNotFound:
        raise HTTPException(status_code=401, detail="Sesión inválida")


@router.patch("/nickname", response_model=ProfileBasic)
async def patch_nickname(
    payload: UpdateNickname,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ProfileBasic:
    try:
        user = await profile_service.update_nickname(session, current_user.id, payload.nickname)
    except profile_service.NicknameAlreadyTaken:
        raise HTTPException(status_code=409, detail="El nickname ya está en uso")
    return _basic_from_user(user)


@router.patch("/password", status_code=status.HTTP_204_NO_CONTENT)
async def patch_password(
    payload: UpdatePassword,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    refresh_cookie = request.cookies.get("refresh_token")
    current_jti: uuid.UUID | None = None
    if refresh_cookie:
        try:
            current_payload = security.verify_token(refresh_cookie, expected_type="refresh")
            current_jti = uuid.UUID(current_payload["jti"])
        except (security.InvalidToken, KeyError, ValueError):
            current_jti = None

    try:
        await profile_service.change_password(
            session,
            user_id=current_user.id,
            current_session_jti=current_jti or uuid.uuid4(),
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    except profile_service.InvalidCurrentPassword:
        raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")
    except profile_service.WeakPasswordError:
        raise HTTPException(status_code=422, detail="La nueva contraseña no cumple los requisitos")

    new_access, _ = security.create_access_token(subject=str(current_user.id))
    new_refresh, _ = security.create_refresh_token(subject=str(current_user.id))
    set_auth_cookies(response, new_access, new_refresh)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.patch("/avatar", response_model=ProfileBasic)
async def patch_avatar(
    payload: UpdateAvatar,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ProfileBasic:
    avatar_str = str(payload.avatar_url) if payload.avatar_url is not None else None
    user = await profile_service.update_avatar(session, current_user.id, avatar_str)
    return _basic_from_user(user)


# ===== US1 (004) — Public profile of another user =======================


@router.get("/{nickname}", response_model=PublicProfileResponse)
async def get_public_profile(
    nickname: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    riot_client=Depends(get_riot_client),
) -> PublicProfileResponse:
    try:
        return await profile_service.get_public_profile(
            session,
            nickname=nickname,
            current_user_id=current_user.id,
            riot_client=riot_client,
        )
    except profile_service.UserNotFound:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")


# ===== US2 — Riot account link / unlink =================================

GENERIC_LINK_ERROR = (
    "No se pudo vincular la cuenta de Riot. Verifica los datos introducidos."
)
RIOT_UNAVAILABLE_ERROR = (
    "Riot no está disponible temporalmente. Inténtalo de nuevo en unos minutos."
)


@router.post(
    "/link/lol",
    response_model=LinkedGameSummary,
    status_code=status.HTTP_201_CREATED,
)
async def post_link_lol(
    payload: LinkRiotAccount,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    riot_client=Depends(get_riot_client),
) -> LinkedGameSummary:
    try:
        account = await profile_service.link_lol(
            session,
            user_id=current_user.id,
            game_name=payload.game_name,
            tag_line=payload.tag_line,
            region=payload.region,
            riot_client=riot_client,
        )
    except profile_service.LinkAccountFailed:
        raise HTTPException(status_code=400, detail=GENERIC_LINK_ERROR)
    except profile_service.RiotUnavailable:
        raise HTTPException(status_code=503, detail=RIOT_UNAVAILABLE_ERROR)
    except profile_service.RiotAlreadyLinked:
        raise HTTPException(
            status_code=409,
            detail="Ya tienes una cuenta de LoL vinculada. Desvincúlala antes de vincular otra.",
        )
    except profile_service.RiotAccountAlreadyClaimed:
        raise HTTPException(
            status_code=409,
            detail="Esta cuenta de LoL ya está vinculada a otro usuario.",
        )

    return LinkedGameSummary(
        game="lol",
        game_name=account.game_name,
        tag_line=account.tag_line,
        region=account.region,
        linked_at=account.linked_at,
    )


@router.delete("/link/lol", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link_lol(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    try:
        await profile_service.unlink_lol(session, current_user.id)
    except profile_service.RiotNotLinked:
        raise HTTPException(status_code=404, detail="No tienes ninguna cuenta de LoL vinculada.")
    except profile_service.UnlinkBlocked:
        raise HTTPException(
            status_code=409,
            detail="No puedes desvincular mientras participes en un torneo activo del juego.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ===== US3 — Delete (anonymize) account =================================

@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    payload: DeleteAccountConfirm,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    refresh_cookie = request.cookies.get("refresh_token")
    active_jtis: list[uuid.UUID] = []
    if refresh_cookie:
        try:
            payload_jwt = security.verify_token(refresh_cookie, expected_type="refresh")
            active_jtis.append(uuid.UUID(payload_jwt["jti"]))
        except (security.InvalidToken, KeyError, ValueError):
            pass

    try:
        await profile_service.delete_account(
            session,
            user_id=current_user.id,
            confirmation=payload.confirmation,
            active_jtis=active_jtis,
        )
    except profile_service.ConfirmationMismatch:
        raise HTTPException(
            status_code=400, detail="La confirmación no coincide con tu nickname."
        )
    except profile_service.DeleteAccountBlocked:
        raise HTTPException(
            status_code=409,
            detail="Tienes torneos activos en curso. Espera a que terminen o abandónalos.",
        )

    secure = security.get_settings().COOKIES_SECURE
    for name in ("access_token", "refresh_token"):
        response.set_cookie(
            name,
            "",
            max_age=0,
            httponly=True,
            secure=secure,
            samesite="lax",
            path="/",
        )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
