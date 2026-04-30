#!/bin/sh
set -e

# Wait briefly for the database to be reachable. asyncpg connects fast once
# Postgres is ready, but the very first compose-up needs a couple of seconds.
echo "[entrypoint] applying alembic migrations..."
alembic upgrade head

echo "[entrypoint] ensuring all model tables exist (top-up for 002-era schema)..."
python - <<'PY'
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.db.base import Base
import app.models  # noqa: F401 — registers all mappers


async def main() -> None:
    engine = create_async_engine(get_settings().DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


asyncio.run(main())
PY

echo "[entrypoint] starting uvicorn on 0.0.0.0:8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
