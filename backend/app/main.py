from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.routes.auth import limiter
from app.api.routes.auth import router as auth_router
from app.core.config import get_settings


async def _rate_limit_handler(request, exc: RateLimitExceeded):
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=429, content={"detail": "Demasiados intentos, inténtelo de nuevo más tarde"})


def _build_allowed_origins(settings) -> list[str]:
    primary = str(settings.FRONTEND_ORIGIN).rstrip("/")
    origins = {primary}
    # Dev convenience: localhost and 127.0.0.1 are distinct origins for the browser.
    if "localhost" in primary:
        origins.add(primary.replace("localhost", "127.0.0.1"))
    elif "127.0.0.1" in primary:
        origins.add(primary.replace("127.0.0.1", "localhost"))
    return sorted(origins)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Competizione Auth API", version="0.1.0")

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
    app.add_middleware(SlowAPIMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_build_allowed_origins(settings),
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    app.include_router(auth_router)
    return app


app = create_app()
