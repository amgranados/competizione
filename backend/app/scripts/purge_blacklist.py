"""I-02: purga las entradas caducadas de `token_blacklist`.

Uso (idealmente desde un cron):
    python -m app.scripts.purge_blacklist

Borra las filas cuyo `expires_at` ya pasó. La columna `expires_at` está indexada,
por lo que el borrado es eficiente y no requiere migración.
"""
from __future__ import annotations

import asyncio
import logging

from app.db.base import AsyncSessionLocal
from app.services import auth_service

logger = logging.getLogger(__name__)


async def _run() -> int:
    async with AsyncSessionLocal() as session:
        deleted = await auth_service.purge_expired_blacklist(session)
    logger.info("purge_blacklist: %s filas caducadas eliminadas", deleted)
    return deleted


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    deleted = asyncio.run(_run())
    print(f"Eliminadas {deleted} entradas caducadas de token_blacklist.")


if __name__ == "__main__":
    main()
