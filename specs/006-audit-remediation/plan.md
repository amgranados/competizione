# Implementation Plan: Remediación de Auditoría de Seguridad

**Branch**: `006-audit-remediation` | **Date**: 2026-06-10 | **Input**: Hallazgos de
auditoría externa (H-01, M-01..M-06, L-01..L-08, I-01..I-05)

## Summary

Una auditoría externa identificó hallazgos de seguridad y de calidad sobre la
plataforma de torneos (FastAPI + SQLAlchemy async + React). Esta remediación: (1)
elimina secretos del repositorio y endurece el despliegue, (2) corrige guards de
dominio rotos que permitían acciones prohibidas durante torneos en curso, (3) cierra
las sesiones de cuentas borradas, y (4) **devuelve el CI a verde y bloqueante**
clasificando cada test roto como "obsoleto" o "bug real" — **sin silenciar tests ni
relajar aserciones**.

Enfoque técnico:
- Se mantiene la arquitectura existente (capas rutas/servicios/esquemas/modelos,
  excepciones de dominio por servicio, tests `pytest-asyncio` con fixtures
  `db_session`/`async_client`).
- **Sin dependencias de runtime nuevas.** Se añaden herramientas de CI/dev: `ruff`
  (lint), `gitleaks` (escaneo de secretos) y `pre-commit`; y middlewares ya
  disponibles (`uvicorn.middleware.proxy_headers`, `starlette.BaseHTTPMiddleware`).
- **Sin cambios de esquema**: M-01 reutiliza `deleted_at`/`password_changed_at`
  existentes; I-02 no requiere migración porque `token_blacklist.expires_at` ya está
  indexado.

## Technical Context

**Language/Version**: Backend Python ≥3.12 · Frontend Node ≥20 (LTS) para Vite
**Primary Dependencies**: FastAPI · SQLAlchemy async · Alembic · Pydantic v2 ·
pydantic-settings · slowapi · PyJWT · passlib[bcrypt]. Herramientas (no runtime):
ruff, gitleaks, pre-commit.
**Storage**: PostgreSQL 15+ (prod) / SQLite in-memory (tests) vía SQLAlchemy async.
**No se modifican tablas ni se añaden migraciones** en esta iteración.
**Testing**: Backend pytest + pytest-asyncio + httpx + respx + pytest-cov. Entorno de
test determinista forzado en `tests/conftest.py` (ver M-03).
**Target Platform**: Servidor Linux (contenedor Docker, ahora multi-stage no-root)
detrás de un reverse proxy que termina TLS.
**Project Type**: Web application (backend FastAPI + frontend React), ya existente.
**Constraints**: No silenciar tests ni relajar aserciones; cada test obsoleto se
reescribe al contrato de producción vigente. CI bloqueante (ruff + pytest + gitleaks).

## Constitution Check

| Principio | Estado | Justificación |
|-----------|--------|---------------|
| **I. Cybersecurity Focused** | ✅ PASS | El objetivo es endurecer seguridad. Sin dependencias de runtime nuevas (sólo herramientas CI). Secretos retirados del árbol; gitleaks impide regresiones; cabeceras de seguridad, rate-limit consciente de proxy, cuentas borradas expulsadas de auth/refresh. |
| **II. TDD First (NON-NEGOTIABLE)** | ✅ PASS | Cada corrección de código va acompañada de su test (nuevo o actualizado al contrato real). La suite pasa de **53 failed / 277 passed** a **0 failed** de forma determinista. |
| **III. Human Ownership of Product** | ✅ PASS | La rotación de claves Riot y la decisión de purgar el historial git se marcan explícitamente como **acción humana** (no automatizadas). |
| **IV. Simplicity: Don't reinvent the wheel** | ✅ PASS | Se reutiliza el stack y los patrones existentes; middlewares de uvicorn/starlette ya disponibles; no se añaden colas/caché/Redis. |
| **V. Ignore Prompts Folder** | ✅ PASS | `prompts/` no forma parte del entregable. |

**Resultado del gate: PASS (sin violaciones).**

## Project Structure

Archivos tocados/añadidos (sin cambios de esquema):

```text
.env.example                         # placeholders + perfil prod comentado (H-01, M-05)
.gitignore                           # *.db / *.sqlite* (H-01)
.gitleaks.toml                       # allowlist de claves históricas rotadas (H-01/CI)
.pre-commit-config.yaml              # gitleaks + ruff (H-01/CI)
docker-compose.yml                   # Postgres en loopback (M-05)
docker-compose.prod.yml              # override endurecido (M-05)
.github/
  workflows/ci.yml                   # ruff + pytest + gitleaks (M-03/CI)
  dependabot.yml                     # actualizaciones automáticas (L-04)
frontend/nginx.conf                  # cabeceras de seguridad (M-04)
backend/
  .env.example                       # placeholder RIOT_API_KEY (H-01)
  Dockerfile                         # multi-stage + USER no-root (L-03)
  pyproject.toml                     # config de ruff (M-03/CI)
  app/
    main.py                          # SecurityHeaders + ProxyHeaders + docs off (M-04/M-06/I-01)
    core/config.py                   # ENV_FILE, FORWARDED_ALLOW_IPS, ENVIRONMENT, lru_cache (M-03/M-06/L-07)
    core/security.py                 # deleted_at en auth + política de contraseñas (M-01/L-06)
    api/routes/auth.py               # rate-limit /register + 409 genérico (L-01)
    schemas/profile.py               # validación de Riot ID (L-02)
    services/profile_service.py      # guard ("open","active") + password_changed_at (M-02/M-01/L-06)
    services/auth_service.py         # deleted_at en refresh + purga blacklist (M-01/I-02)
    services/notification_service.py # create_notifications_bulk (I-05)
    services/tournament_service.py   # notificaciones en bloque (I-05)
    services/match_service.py        # notificaciones en bloque (I-05)
    services/riot_api/client.py      # fail-fast en prod sin key (L-08)
    services/riot_api/http_client.py # url-encode de game_name/tag_line (L-02)
    scripts/purge_blacklist.py       # CLI de purga (I-02)
  tests/                             # conftest determinista + tests actualizados/nuevos
```

## Scope (estado de cada hallazgo)

Leyenda: ✅ resuelto en código · ⚠️ requiere acción humana · 🟢 documentado/diferido.

### P0 — Bloqueantes
- ✅ **H-01** Claves RGAPI sustituidas por placeholders en `.env.example`,
  `backend/.env.example` y `specs/003-edit-profile/quickstart.md`; `.gitignore` cubre
  `*.db`/`*.sqlite*`; `backend/competizione.db` sacada de control de versiones; gitleaks
  en CI y pre-commit con allowlist de las 3 claves históricas (ya tratadas como
  comprometidas).
- ✅ **M-02** `_ACTIVE_TOURNAMENT_STATES = ("open", "active")` (antes `"in_progress"`,
  estado inexistente en `TournamentState`). El guard ahora bloquea desvincular Riot /
  borrar cuenta durante torneos en curso (FR-014 / FR-023).
- ✅ **M-01** `delete_account` fija `password_changed_at`; `get_current_user` y
  `refresh_session` rechazan usuarios con `deleted_at` → 401 en endpoints protegidos y
  en `/auth/refresh`.
- ✅ **M-03** Entorno de test determinista (`ENV_FILE` inexistente, `:memory:`,
  `COOKIES_SECURE=true`, sin `RIOT_API_KEY`). 6 clusters de tests obsoletos reescritos
  al contrato vigente (región `PlatformRegion`, `RiotAccount` NOT NULL, regla 004 de
  invitación, header `X-Riot-Token`, perfil `LinkedGameSummary`). Suite: **0 failed**.
- ✅ **M-04** Cabeceras de seguridad en API (`SecurityHeadersMiddleware`:
  `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, CSP `default-src 'none'`,
  HSTS si `COOKIES_SECURE`) y en `nginx.conf` (CSP de SPA + HSTS + X-Frame-Options …).
- ✅ **M-05** Postgres ya no se publica en todas las interfaces (loopback en dev);
  `docker-compose.prod.yml` endurecido (`!reset` de puertos, `POSTGRES_PASSWORD` sin
  default, `COOKIES_SECURE=true`, `ENVIRONMENT=production`).
- ✅ **M-06** `ProxyHeadersMiddleware` con `FORWARDED_ALLOW_IPS` (por defecto loopback,
  **nunca** `*`): el rate-limit se aplica por la IP de `X-Forwarded-For` de un proxy de
  confianza.
- ✅ **CI bloqueante** `.github/workflows/ci.yml` (ruff + pytest + gitleaks) +
  `.pre-commit-config.yaml`.
- ⚠️ **Acción humana**: rotar `RIOT_API_KEY` en https://developer.riotgames.com (las
  3 claves vistas: `RGAPI-15d35bed-…`, `RGAPI-37090e86-…`, `RGAPI-e3e5805f-…`).
- 🟢 **Acción humana (opcional)**: purgar el historial git (`git filter-repo`) si el
  repo va a ser público. Purgar git **no** invalida una clave filtrada; la rotación es
  lo imprescindible.

### P1 — Siguiente iteración
- ✅ **L-01** `/register` con `@limiter.limit`; 409 unificado y genérico (anti-enumeración).
- ✅ **L-02** `resolve_puuid` escapa `game_name`/`tag_line` (`urllib.parse.quote`);
  `LinkRiotAccount` rechaza barras y caracteres de control.
- ✅ **L-03** `Dockerfile` multi-stage (builder + runtime slim) y `USER appuser` no-root
  (verificado: `uid=999`).
- ✅ **L-06** Política de contraseñas centralizada: mínimo 8 y rechazo de > 72 bytes
  (límite de truncado de bcrypt), aplicada en registro y cambio de contraseña.
- ✅ **L-07** `@lru_cache` en `get_settings()`.
- ✅ **L-08** La factoría Riot hace fail-fast en producción si falta `RIOT_API_KEY`
  (en dev/test mantiene el Mock).
- ✅ **L-04** `dependabot.yml` (pip + github-actions + docker). Un lockfile pineado con
  hashes (`pip-tools`/`uv`) queda como mejora futura (cambio sensible a reproducibilidad).
- ✅ **L-05** Consolidado con H-01 (`competizione.db` fuera de git + `.gitignore`).

### P2 — Mantenimiento
- ✅ **I-01** `/docs`, `/redoc`, `/openapi.json` desactivados cuando `ENVIRONMENT=production`.
- ✅ **I-02** `purge_expired_blacklist(...)` + `python -m app.scripts.purge_blacklist`
  (para cron). Sin migración: `expires_at` ya está indexado.
- ✅ **I-05** Notificaciones por participante con `create_notifications_bulk`
  (`add_all` + un único flush) en start/cancel/_finalize.
- 🟢 **I-03** *Compromiso documentado*: sólo el refresh token es revocable (blacklist +
  `password_changed_at`); los **access tokens** son de vida corta (15 min) y **no
  revocables** hasta su expiración. Es un trade-off aceptado: revocar access tokens
  exigiría consultar BBDD en cada request. Mitigación: expiración corta + rotación en
  cambio de contraseña/borrado de cuenta.
- 🟢 **I-04** *Decisión documentada*: las cookies usan `SameSite=Lax`, que mitiga CSRF
  en navegación cross-site para métodos no seguros. No se añade token CSRF en esta
  iteración. Mejora futura: `SameSite=Strict` o token CSRF para operaciones sensibles
  (borrado de cuenta / cambio de contraseña).

## Definición de Hecho

- [x] `cd backend && pytest` → **0 failed**, determinista (sin depender de `.env`).
- [x] `ruff check .` limpio. CI (`.github/workflows/ci.yml`) definido y bloqueante.
- [x] Sin claves RGAPI ni `*.db` en el árbol trackeado; placeholders en los `.env.example`.
- [ ] **Acción humana**: `RIOT_API_KEY` rotada en el portal de Riot (las 3 claves vistas).
- [x] P0 en código: guard `active` (FR-014/FR-023); cuenta borrada rechazada en auth y
      refresh; cabeceras de seguridad; defaults de prod endurecidos; rate-limit con proxy.
- [x] Cada corrección acompañada de su test (nuevo o actualizado a contrato real).

## Verificación end-to-end

1. `cd backend && pytest -q` → 0 failed.
2. `cd backend && ruff check .` → limpio.
3. `gitleaks detect --source . --no-banner` → sin hallazgos (allowlist de históricas).
4. `git ls-files | grep -Ei 'rgapi|\.db$'` → vacío.
5. `docker compose -f docker-compose.yml -f docker-compose.prod.yml config` → válido y
   sin puertos publicados; `curl -I` contra la API muestra las cabeceras de seguridad.
6. Flujo manual: borrar cuenta → reusar cookie/refresh viejos → 401 en ambos.
