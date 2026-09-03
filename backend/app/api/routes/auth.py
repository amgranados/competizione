from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.db.base import get_db
from app.models.user import User
from app.schemas.auth import AuthenticatedUser, ErrorResponse, LoginRequest, RegisterRequest
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

GENERIC_ERROR = "Credenciales inválidas"
# L-01: mensaje genérico de registro para no revelar si el conflicto fue por
# email o por nickname (evita enumeración de cuentas existentes).
GENERIC_REGISTER_CONFLICT = "No se pudo completar el registro con esos datos"
IP_RATE_LIMIT_ENABLED = True
IP_RATE_LIMIT_RULE = "5/minute"

limiter = Limiter(key_func=get_remote_address, default_limits=[])


async def get_current_user(request: Request, session: AsyncSession = Depends(get_db)) -> User:
    try:
        return await security.get_current_user(request, session)
    except security.InvalidToken:
        raise HTTPException(status_code=401, detail=GENERIC_ERROR)
    except ValueError:
        raise HTTPException(status_code=401, detail=GENERIC_ERROR)


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        "access_token",
        access_token,
        max_age=security.access_token_max_age_seconds(),
        httponly=True,
        secure=security.get_settings().COOKIES_SECURE,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        max_age=security.refresh_token_max_age_seconds(),
        httponly=True,
        secure=security.get_settings().COOKIES_SECURE,
        samesite="lax",
        path="/",
    )


@router.post(
    "/register",
    response_model=AuthenticatedUser,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
@limiter.limit(IP_RATE_LIMIT_RULE, exempt_when=lambda: not IP_RATE_LIMIT_ENABLED)
async def register(
    request: Request,
    payload: RegisterRequest,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> AuthenticatedUser:
    try:
        user = await auth_service.register_user(session, payload)
    except security.PasswordPolicyError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except (auth_service.EmailAlreadyRegistered, auth_service.NicknameAlreadyTaken):
        # L-01: 409 unificado (no distinguir email vs nickname) para no filtrar
        # qué dato ya existe.
        raise HTTPException(status_code=409, detail=GENERIC_REGISTER_CONFLICT)
    except auth_service.NicknameGenerationExhausted:
        raise HTTPException(status_code=500, detail="No se pudo asignar un nickname único")

    access_token, _ = security.create_access_token(subject=str(user.id))
    refresh_token, _ = security.create_refresh_token(subject=str(user.id))
    set_auth_cookies(response, access_token, refresh_token)

    return AuthenticatedUser.model_validate(user)


@router.get(
    "/me",
    response_model=AuthenticatedUser,
    responses={401: {"model": ErrorResponse}},
)
async def me(current_user: User = Depends(get_current_user)) -> AuthenticatedUser:
    return AuthenticatedUser.model_validate(current_user)


@router.post(
    "/login",
    response_model=AuthenticatedUser,
    status_code=status.HTTP_200_OK,
    responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
@limiter.limit(IP_RATE_LIMIT_RULE, exempt_when=lambda: not IP_RATE_LIMIT_ENABLED)
async def login(
    request: Request,
    payload: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> AuthenticatedUser:
    try:
        user = await auth_service.authenticate_user(session, payload.email, payload.password)
    except auth_service.InvalidCredentials:
        raise HTTPException(status_code=401, detail=GENERIC_ERROR)

    access_token, _ = security.create_access_token(subject=str(user.id))
    refresh_token, _ = security.create_refresh_token(subject=str(user.id))
    set_auth_cookies(response, access_token, refresh_token)

    return AuthenticatedUser.model_validate(user)


@router.post(
    "/refresh",
    response_model=AuthenticatedUser,
    status_code=status.HTTP_200_OK,
    responses={401: {"model": ErrorResponse}},
)
async def refresh(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> AuthenticatedUser:
    try:
        user, access_token, refresh_token = await auth_service.refresh_session(
            session, request.cookies.get("refresh_token")
        )
    except auth_service.InvalidCredentials:
        raise HTTPException(status_code=401, detail=GENERIC_ERROR)

    set_auth_cookies(response, access_token, refresh_token)
    return AuthenticatedUser.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> Response:
    await auth_service.logout_session(session, request.cookies.get("refresh_token"))
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
