"""Integration tests for security headers (M-04) and proxy-aware rate limit (M-06)."""
from __future__ import annotations

import pytest

from tests.helpers import register_user


@pytest.mark.asyncio
async def test_security_headers_present_on_response(async_client):
    """Toda respuesta de la API lleva las cabeceras de seguridad base (M-04)."""
    await register_user(async_client, "alice@example.com", "alice")
    resp = await async_client.get("/api/profile")
    assert resp.status_code == 200

    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "no-referrer"
    assert "default-src 'none'" in resp.headers["Content-Security-Policy"]


@pytest.mark.asyncio
async def test_security_headers_present_on_error_response(async_client):
    """Las cabeceras también aparecen en respuestas de error (p. ej. 401)."""
    async_client.cookies.clear()
    resp = await async_client.get("/api/profile")
    assert resp.status_code == 401
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"


@pytest.mark.asyncio
async def test_hsts_present_when_cookies_secure(async_client):
    """En el entorno de test COOKIES_SECURE=true ⇒ se emite HSTS."""
    async_client.cookies.clear()
    resp = await async_client.get("/api/profile")
    assert "Strict-Transport-Security" in resp.headers
    assert "max-age=" in resp.headers["Strict-Transport-Security"]


@pytest.mark.asyncio
async def test_rate_limit_keys_by_forwarded_ip(async_client, monkeypatch):
    """M-06: el rate-limit se aplica por la IP de X-Forwarded-For (de un proxy de
    confianza), de modo que distintos clientes detrás del proxy no comparten cupo
    y un cliente no puede agotar el de otro."""
    from app.api.routes import auth as auth_routes

    monkeypatch.setattr(auth_routes, "IP_RATE_LIMIT_ENABLED", True)
    auth_routes.limiter.reset()

    ip_a = {"X-Forwarded-For": "203.0.113.10"}
    ip_b = {"X-Forwarded-For": "203.0.113.20"}

    # Agota el cupo (5/min) de la IP A → la 6ª es 429.
    for _ in range(5):
        r = await async_client.post(
            "/auth/login",
            json={"email": "x@example.com", "password": "whatever-long"},
            headers=ip_a,
        )
        assert r.status_code == 401
    blocked = await async_client.post(
        "/auth/login",
        json={"email": "x@example.com", "password": "whatever-long"},
        headers=ip_a,
    )
    assert blocked.status_code == 429

    # La IP B mantiene su propio cupo: su primer intento NO está bloqueado.
    other = await async_client.post(
        "/auth/login",
        json={"email": "x@example.com", "password": "whatever-long"},
        headers=ip_b,
    )
    assert other.status_code != 429, other.text
