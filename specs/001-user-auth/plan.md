# Implementation Plan: Autenticación de usuarios

**Branch**: `001-user-auth` | **Date**: 2026-04-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-user-auth/spec.md`
**Stack input (human)**: `prompts/second/01-autenticacion.txt` — el humano ha fijado explícitamente el stack, librerías, estructura de carpetas y restricciones técnicas. Este plan lo asume sin cuestionarlo (Constitución IV).

## Summary

Sistema de autenticación para aplicación web con datos personales sensibles. Backend Python/FastAPI expone endpoints REST de auth; frontend React (Vite) consume la API y gestiona las rutas protegidas. La sesión se implementa como **access JWT (HS256, 15 min) + refresh JWT (HS256, 7 días)** enviados exclusivamente en **cookies HttpOnly + Secure + SameSite=lax**; el refresh token se **rota en cada uso** y el anterior queda en una **blacklist en PostgreSQL**. Contraseñas hasheadas con **bcrypt via passlib**. Rate limiting con **slowapi** (5 intentos/min por IP en `POST /auth/login`). CORS restringido al origen del frontend.

## Technical Context

**Language/Version**: Backend **Python ≥3.12** (FastAPI requiere 3.8+, usamos el LTS reciente). Frontend **Node ≥20 (LTS)** para Vite.
**Primary Dependencies**:
- Backend: FastAPI, SQLAlchemy 2.x (async), Alembic, Pydantic v2, **PyJWT** (sustituye a python-jose tras la decisión humana sobre CVE audit), passlib[bcrypt], **python-multipart ≥0.0.9** (fija CVE-2024-24762), slowapi, pydantic-settings.
- Frontend: React 18+, Vite, **React Router v6 ≥6.22**, `fetch` nativo con `credentials: "include"` (explícitamente **sin** axios ni localStorage).
- Auditoría CVE completa en `research.md § CVE Audit`. Todos los hallazgos están resueltos o mitigados por las versiones mínimas acordadas.
**Storage**: **PostgreSQL 15+** accedido con SQLAlchemy async. Migraciones con Alembic. Blacklist de refresh tokens persiste en BBDD (no Redis).
**Testing**:
- Backend: **pytest**, pytest-asyncio, httpx (cliente de test FastAPI), pytest-cov.
- Frontend: **Vitest**, @testing-library/react, @testing-library/user-event, msw para mock de fetch.
- **Principio II (NO NEGOCIABLE)**: todo código productivo nace de un test fallido (Red → Green → Refactor). Ver `research.md § TDD Workflow`.
**Target Platform**: Servidor Linux. HTTPS obligatorio en producción (cookies `Secure=True` lo exigen). Despliegue concreto a confirmar (no bloquea este plan).
**Project Type**: **Backend API + Frontend SPA separados** (Variante B del cuestionario). Estructura fijada por el humano en el prompt.
**Performance Goals**: No especificado. Objetivo indicativo: p95 de `/auth/login` < 500 ms bajo carga de prueba. Confirmar si hay SLA.
**Constraints**:
- Tokens viajan **sólo** en cookies HttpOnly; jamás en response body (restricción del prompt).
- Mensajes de error de login siempre genéricos: `"Credenciales inválidas"` (spec FR-008 y prompt).
- Contraseña mínimo 8 caracteres, validada en backend (Pydantic).
- IDs de usuario UUID v4.
- CORS restringido al `FRONTEND_ORIGIN`.
- `SECRET_KEY` ≥32 caracteres desde variable de entorno (nunca commitear).
- Respuestas indistinguibles por timing cuando el email no existe: se ejecuta un *dummy hash* verificación para no filtrar por latencia (ver `research.md § Timing attack mitigation`).
**Scale/Scope**: Primera versión, tamaño pequeño/medio. No se fija SLA concreto.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Evaluación frente a `.specify/memory/constitution.md` (v1.0.0, 2026-04-21).

**Pre-Phase 0 (stack ya fijado por humano):**

| Principio | Estado | Notas |
|-----------|--------|-------|
| I. Cybersecurity Focused | **OK** | Auditoría CVE ejecutada (`research.md § CVE Audit`) y aprobada por el humano: python-jose → **PyJWT** (Auth0, mantenida); `python-multipart>=0.0.9` fija CVE-2024-24762; `react-router-dom>=6.22` fija advisory 2024. No se instalará nada sin aplicar estos pins. |
| II. TDD First (NO NEGOCIABLE) | **OK** | pytest y Vitest seleccionados. Fase 1 define el orden Red → Green → Refactor por FR en `tasks.md` (Fase 2). |
| III. Human Ownership of Product | **OK** | Decisiones técnicas se explican en `research.md` con fuentes (OWASP, documentación oficial, NVD, GitHub Advisory). Diagramas en `contracts/*.puml`. |
| IV. Simplicity: Don't reinvent the wheel | **OK** | Stack, librerías y estructura de carpetas impuestas por el humano y respetadas literalmente. No se sustituye ni se "mejora" nada. |
| V. Ignore Prompts Folder | **OK** | `prompts/` se trata sólo como fuente de input histórica; no se añade código, dependencias ni rutas que lo referencien en tiempo de ejecución. |

**Resultado pre-Phase 0**: **PASA**. Se procede con Fase 0 y Fase 1.

**Post-Phase 1 (re-check tras diseño)**: el diseño no introduce dependencias nuevas; ver `research.md § Post-Design Re-check` y `data-model.md`. **PASA sin observaciones**.

## Project Structure

### Documentation (this feature)

```text
specs/001-user-auth/
├── plan.md
├── research.md                # Fase 0 — decisiones + CVE audit
├── data-model.md              # Fase 1 — User, TokenBlacklist, FailedLoginAttempt
├── quickstart.md              # Fase 1 — puesta en marcha + flujo TDD
├── contracts/
│   ├── auth.openapi.yaml      # Fase 1 — contrato OpenAPI 3.1
│   ├── auth-flow.puml         # Fase 1 — secuencia: register/login/refresh/logout
│   └── session-lifecycle.puml # Fase 1 — estados de sesión y refresh rotation
├── checklists/
│   └── requirements.md        # /speckit.specify
└── tasks.md                   # Fase 2 — /speckit.tasks (no por este comando)
```

### Source Code (repository root)

Estructura fijada literalmente por el humano en `prompts/second/01-autenticacion.txt`:

```text
backend/
├── app/
│   ├── api/
│   │   └── routes/
│   │       └── auth.py
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   ├── db/
│   │   ├── base.py
│   │   └── migrations/
│   ├── models/
│   │   ├── user.py
│   │   └── token_blacklist.py
│   ├── schemas/
│   │   └── auth.py
│   ├── services/
│   │   └── auth_service.py
│   └── main.py
├── tests/
│   ├── conftest.py            # fixtures: cliente de test, DB de test
│   ├── unit/
│   │   ├── test_security.py   # hash, verify_password, create_token, verify_token
│   │   └── test_auth_service.py
│   └── integration/
│       └── test_auth_routes.py  # register, login, refresh, logout end-to-end

frontend/
├── src/
│   ├── api/
│   │   └── authApi.js
│   ├── context/
│   │   └── AuthContext.jsx
│   ├── hooks/
│   │   └── useAuth.js
│   ├── components/
│   │   └── ProtectedRoute.jsx
│   ├── pages/
│   │   ├── Login.jsx
│   │   └── Register.jsx
│   └── main.jsx
├── tests/
│   ├── setup.js
│   ├── mocks/
│   │   └── authHandlers.js
│   ├── unit/
│   │   └── useAuth.test.js
│   └── integration/
│       ├── Login.test.jsx
│       ├── Register.test.jsx
│       └── ProtectedRoute.test.jsx
```

**Structure Decision**: Variante B (API + SPA) con la estructura literal impuesta por el humano. No se añaden carpetas ni ficheros fuera de esa lista salvo los generados por `alembic init` dentro de `backend/app/db/migrations/` y los ficheros estándar del proyecto (`pyproject.toml`/`requirements.txt`, `package.json`, `vite.config.js`, `pytest.ini`, `alembic.ini`, `.env.example`).

## Decisiones humanas resueltas (trazabilidad)

Todas las ambigüedades spec↔prompt fueron consultadas al humano (Constitución III/IV) y quedan fijadas:

- **JWT library**: python-jose sustituido por **PyJWT** (opción B) tras la CVE audit. Ver `research.md § D2`.
- **Rate limiting per-account (spec FR-017)**: **aprobado** el mecanismo `failed_login_attempts` + `locked_until` en `User`, con umbral **10 intentos en 15 min ⇒ lock 15 min**. **Reset explícito del contador en cada login exitoso.** Ver `research.md § D5` y `data-model.md`.
- **`GET /auth/me`**: **mantener**. El frontend lo usa para detectar si hay sesión sin leer cookies HttpOnly.
- **Versiones mínimas aceptadas**: `python-multipart>=0.0.9` y `react-router-dom>=6.22`.

Decisiones derivadas (sin gap, aplicadas conforme a spec):

- **Nickname auto-generado (FR-003)**: `services/auth_service.py::generate_unique_nickname()` reintenta hasta encontrar un `user<5-dígitos>` libre apoyándose en la unicidad a nivel de BBDD (atomicidad garantizada).

## Complexity Tracking

> Sin violaciones. Todas las elecciones vienen impuestas por el humano; este plan no introduce abstracciones propias.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (ninguna) | — | — |
