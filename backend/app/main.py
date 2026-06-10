from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.api.routes.auth import limiter
from app.api.routes.auth import router as auth_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.friends import router as friends_router
from app.api.routes.matches import router as matches_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.profile import router as profile_router
from app.api.routes.tournaments import router as tournaments_router
from app.core.config import get_settings


async def _rate_limit_handler(request, exc: RateLimitExceeded):
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=429, content={"detail": "Demasiados intentos, inténtelo de nuevo más tarde"})


# M-04 — Cabeceras de seguridad en todas las respuestas de la API. La API sirve
# JSON (no HTML navegable), así que la CSP puede ser máximamente restrictiva.
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Añade cabeceras de seguridad. HSTS sólo cuando se sirve sobre HTTPS
    (aproximado por COOKIES_SECURE) para no romper el desarrollo local en HTTP."""

    def __init__(self, app, *, hsts: bool):
        super().__init__(app)
        self._hsts = hsts

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        for header, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        if self._hsts:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=63072000; includeSubDomains",
            )
        return response


def _build_allowed_origins(settings) -> list[str]:
    primary = str(settings.FRONTEND_ORIGIN).rstrip("/")
    origins = {primary}
    # Dev convenience: localhost and 127.0.0.1 are distinct origins for the browser.
    if "localhost" in primary:
        origins.add(primary.replace("localhost", "127.0.0.1"))
    elif "127.0.0.1" in primary:
        origins.add(primary.replace("127.0.0.1", "localhost"))
    return sorted(origins)


def _is_production(settings) -> bool:
    return settings.ENVIRONMENT.strip().lower() in ("prod", "production")


def create_app() -> FastAPI:
    settings = get_settings()

    # I-01: no exponer la documentación interactiva ni el esquema en producción.
    docs_kwargs: dict = {}
    if _is_production(settings):
        docs_kwargs = {"docs_url": None, "redoc_url": None, "openapi_url": None}

    app = FastAPI(title="Competizione Auth API", version="0.1.0", **docs_kwargs)

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

    # Orden de middlewares (el último añadido es el más externo):
    #   1) ProxyHeaders (más externo): corrige request.client desde X-Forwarded-For
    #      de proxies de confianza ANTES de que el rate-limit lea la IP (M-06).
    #   2) SecurityHeaders: añade cabeceras a la respuesta (M-04).
    #   3) CORS.
    #   4) SlowAPI (más interno): aplica el rate-limit por IP ya corregida.
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_build_allowed_origins(settings),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )
    app.add_middleware(SecurityHeadersMiddleware, hsts=settings.COOKIES_SECURE)
    app.add_middleware(
        ProxyHeadersMiddleware,
        trusted_hosts=settings.FORWARDED_ALLOW_IPS,
    )

    app.include_router(auth_router)
    app.include_router(tournaments_router)
    app.include_router(matches_router)
    app.include_router(notifications_router)
    app.include_router(profile_router)
    app.include_router(friends_router)
    app.include_router(dashboard_router)
    return app


app = create_app()
