import os
from collections.abc import AsyncIterator

# --- Entorno de test determinista ----------------------------------------
# La suite DEBE ser independiente de cualquier `.env` presente en disco
# (p. ej. backend/.env con COOKIES_SECURE=false, una RIOT_API_KEY real y
# DATABASE_URL apuntando a la BBDD versionada). Para ello:
#   1. Apuntamos ENV_FILE a una ruta inexistente => Settings no carga ningún
#      `.env`; sólo lee variables de entorno explícitas.
#   2. Fijamos las variables con asignación directa (override autoritativo),
#      NO con setdefault, de modo que el entorno de test SIEMPRE gana.
#   3. Eliminamos RIOT_API_KEY del entorno => la factoría usa MockRiotAPIClient
#      y los tests no consumen la Riot API real.
os.environ["ENV_FILE"] = os.path.join(os.path.dirname(__file__), ".env.tests-nonexistent")
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SECRET_KEY"] = "x" * 48
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "15"
os.environ["REFRESH_TOKEN_EXPIRE_DAYS"] = "7"
os.environ["FRONTEND_ORIGIN"] = "http://localhost:5173"
os.environ["COOKIES_SECURE"] = "true"
os.environ.pop("RIOT_API_KEY", None)

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db.base import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def async_client(db_engine, monkeypatch) -> AsyncIterator[AsyncClient]:
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    from app.api.routes import auth as auth_routes

    monkeypatch.setattr(auth_routes, "IP_RATE_LIMIT_ENABLED", False)
    auth_routes.limiter.reset()

    app.dependency_overrides[get_db] = _override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _anyio_backend():
    return "asyncio"
