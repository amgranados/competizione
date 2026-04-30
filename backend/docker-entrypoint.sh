#!/bin/sh
set -e

echo "[entrypoint] applying alembic migrations..."
alembic upgrade head

echo "[entrypoint] starting uvicorn on 0.0.0.0:8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
