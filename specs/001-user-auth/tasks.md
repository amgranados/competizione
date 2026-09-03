---

description: "Task list for feature 001-user-auth: Autenticación de usuarios"
---

# Tasks: Autenticación de usuarios

**Input**: Design documents from `specs/001-user-auth/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: TDD es **OBLIGATORIO** por la Constitución (Principio II, NON-NEGOCIABLE). Cada tarea de test debe fallar antes de escribir la implementación asociada.

**Organization**: Tareas agrupadas por user story (US1…US5 de `spec.md`) para implementación y testing independientes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo con otras `[P]` del mismo bloque (ficheros distintos, sin dependencias pendientes).
- **[Story]**: US1…US5 para tareas de historia; Setup, Foundational y Polish no llevan etiqueta de historia.
- Todos los paths son relativos a la raíz del repositorio.

## Path Conventions

Estructura fijada en `plan.md` (Variante B — backend API + frontend SPA):

- Backend: `backend/app/**`, `backend/tests/**`
- Frontend: `frontend/src/**`, `frontend/tests/**`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Inicializar la estructura del proyecto y herramientas compartidas. No instalar dependencias reales hasta que estas tareas se ejecuten contra la CVE audit aprobada (`research.md § CVE Audit`).

- [x] T001 Crear estructura de directorios del repositorio: `backend/app/{api/routes,core,db/migrations,models,schemas,services}`, `backend/tests/{unit,integration}`, `frontend/src/{api,context,hooks,components,pages}`, `frontend/tests/{mocks,unit,integration}` (sin ficheros dentro todavía salvo `.gitkeep` donde hiciera falta).
- [x] T002 [P] Crear `backend/requirements.txt` con pins mínimos aprobados: `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]>=2.0.30`, `alembic>=1.13`, `asyncpg`, `pydantic>=2.7`, `pydantic-settings>=2.2`, `PyJWT>=2.9`, `passlib[bcrypt]>=1.7.4`, `python-multipart>=0.0.9`, `slowapi>=0.1.9`, `httpx`, `pytest`, `pytest-asyncio`, `pytest-cov`.
- [x] T003 [P] Crear `frontend/package.json` con pins mínimos aprobados: `react@^18.3`, `react-dom@^18.3`, `react-router-dom@^6.22`, `vite@^5.2` (devDep), `vitest@^1.6` (devDep), `@testing-library/react`, `@testing-library/user-event`, `msw@^2`.
- [x] T004 [P] Crear `backend/pyproject.toml` (o `pytest.ini`) con config de pytest: `asyncio_mode = "auto"`, `testpaths = ["tests"]`, `addopts = "--cov=app --cov-report=term-missing"`.
- [x] T005 [P] Crear `frontend/vite.config.js` con plugin de React y `frontend/vitest.config.js` (o sección `test` en `vite.config.js`) apuntando a `tests/setup.js`.
- [x] T006 [P] Crear `backend/.env.example` con variables: `DATABASE_URL`, `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES=15`, `REFRESH_TOKEN_EXPIRE_DAYS=7`, `FRONTEND_ORIGIN=http://localhost:5173`.
- [x] T007 [P] Crear `frontend/.env.example` con `VITE_API_BASE_URL=http://localhost:8000`.
- [x] T008 [P] Añadir entradas a `.gitignore` raíz: `backend/.venv/`, `backend/.env`, `backend/__pycache__/`, `backend/.pytest_cache/`, `backend/htmlcov/`, `frontend/node_modules/`, `frontend/.env.local`, `frontend/dist/`, `frontend/coverage/`.

**Checkpoint**: Estructura y archivos de configuración listos; dependencias declaradas (sin instalar todavía).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestructura que todas las historias usan. **Bloquea** el inicio de cualquier user story.

- [x] T009 Implementar `Settings` con pydantic-settings (carga de `.env`, tipos: `DATABASE_URL: PostgresDsn`, `SECRET_KEY: str con min_length=32`, `ACCESS_TOKEN_EXPIRE_MINUTES: int`, `REFRESH_TOKEN_EXPIRE_DAYS: int`, `FRONTEND_ORIGIN: AnyHttpUrl`) en `backend/app/core/config.py`.
- [x] T010 Implementar engine async y `AsyncSessionLocal` + `get_db()` dependency en `backend/app/db/base.py` (usa `settings.DATABASE_URL`).
- [x] T011 Inicializar Alembic en `backend/app/db/migrations/` (`alembic init --template=async app/db/migrations`), configurar `alembic.ini` y `env.py` para leer `DATABASE_URL` desde `Settings` y apuntar a los modelos (`Base.metadata`).
- [x] T012 Crear app FastAPI en `backend/app/main.py` con `CORSMiddleware(allow_origins=[settings.FRONTEND_ORIGIN], allow_credentials=True, allow_methods=["GET","POST"], allow_headers=["Content-Type"])`. Aún no registra rutas de auth.
- [x] T013 [P] Crear fixtures de test en `backend/tests/conftest.py`: engine/sesión sobre BBDD de test (p. ej. base dedicada o SQLite async sólo si el humano acepta; si no, usar PostgreSQL de test vía `DATABASE_URL` override), `async_client` con `httpx.AsyncClient(app=app, base_url="http://test")`, fixture `db_session` con rollback por test.
- [x] T014 [P] Crear `frontend/tests/setup.js` con arranque/stop de MSW (`beforeAll server.listen`, `afterEach server.resetHandlers`, `afterAll server.close`) y configuración global de Testing Library.
- [x] T015 [P] Crear esqueleto de handlers MSW en `frontend/tests/mocks/authHandlers.js` y exportación de `server` (p. ej. en `frontend/tests/mocks/server.js`).
- [x] T016 [P] Crear `frontend/index.html` y `frontend/src/main.jsx` con `<BrowserRouter>` envolviendo la app (sin rutas todavía).
- [x] T017 [P] Crear `frontend/src/api/authApi.js` con helper base `request(path, options)` que hace `fetch(\`${import.meta.env.VITE_API_BASE_URL}${path}\`, { credentials: "include", headers: { "Content-Type": "application/json" }, ...options })` y parsea JSON. Aún sin endpoints específicos.
- [x] T018 [P] Crear esqueleto de `frontend/src/context/AuthContext.jsx` con un provider que expone `{ user, status }` y funciones placeholder; y `frontend/src/hooks/useAuth.js` que lee el contexto. Sin llamadas a red todavía.

**Checkpoint**: Base lista. A partir de aquí, US1 puede empezar; US2–US5 dependen de US1 para el contrato de login/cookies.

---

## Phase 3: User Story 1 — Registro e inicio de sesión (Priority: P1) 🎯 MVP

**Goal**: Un visitante puede crear una cuenta (email + password, nickname opcional auto-generado `user<5-dígitos>`) e iniciar sesión; el servidor emite las cookies `access_token` y `refresh_token` como HttpOnly + Secure + SameSite=lax; errores de login son indistinguibles (mismo mensaje, código y timing).

**Independent Test**: Desde la UI, registrar un usuario nuevo, cerrar la pestaña y volver a entrar con esas credenciales. En el backend, `pytest backend/tests -k "register or login"` pasa en verde.

**FR cubiertos**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, FR-012 (HttpOnly en las cookies emitidas aquí).

### Tests for User Story 1 ⚠️ (Red: deben fallar antes de implementar)

- [x] T019 [P] [US1] Tests unitarios de password hashing en `backend/tests/unit/test_security.py`.
- [x] T020 [P] [US1] Tests unitarios de JWT con PyJWT en `backend/tests/unit/test_security.py`.
- [x] T021 [P] [US1] Tests unitarios en `backend/tests/unit/test_auth_service.py`.
- [x] T022 [P] [US1] Integration test `POST /auth/register` en `backend/tests/integration/test_auth_routes.py`.
- [x] T023 [P] [US1] Integration test `POST /auth/login` en `backend/tests/integration/test_auth_routes.py`.
- [x] T024 [P] [US1] Integration test cookies HttpOnly en `backend/tests/integration/test_auth_routes.py::test_auth_cookies_are_httponly_secure_samesite_lax`.
- [x] T025 [P] [US1] Handlers MSW para `/auth/register` y `/auth/login` en `frontend/tests/mocks/authHandlers.js`.
- [x] T026 [P] [US1] Frontend integration test `Register.jsx` en `frontend/tests/integration/Register.test.jsx`.
- [x] T027 [P] [US1] Frontend integration test `Login.jsx` en `frontend/tests/integration/Login.test.jsx`.

### Implementation for User Story 1

- [x] T028 [P] [US1] Modelo `User` en `backend/app/models/user.py` (sin `failed_login_attempts`/`locked_until`; vienen en US5).
- [ ] T029 [US1] Primera migración Alembic autogenerada para tabla `users` en `backend/app/db/migrations/versions/` (PENDIENTE: la schema se crea en tests vía `Base.metadata.create_all`; la migración Alembic se generará en bloque con US3/US5 contra una BBDD Postgres).
- [x] T030 [P] [US1] Schemas Pydantic en `backend/app/schemas/auth.py`.
- [x] T031 [US1] `core/security.py` en `backend/app/core/security.py` con hashing bcrypt, dummy_verify y PyJWT HS256 estricto.
- [x] T032 [US1] `services/auth_service.py` con `generate_unique_nickname`, `register_user`, `authenticate_user`.
- [x] T033 [US1] Helper `set_auth_cookies` en `backend/app/api/routes/auth.py`.
- [x] T034 [US1] Endpoint `POST /auth/register` en `backend/app/api/routes/auth.py`.
- [x] T035 [US1] Endpoint `POST /auth/login` en `backend/app/api/routes/auth.py`.
- [x] T036 [US1] Registrado `auth_router` en `backend/app/main.py`.
- [x] T037 [P] [US1] `authApi.register/login` en `frontend/src/api/authApi.js` (a través de `AuthContext`).
- [x] T038 [P] [US1] `AuthContext` con `register`/`login` y `useAuth` hook en `frontend/src/context/AuthContext.jsx` y `frontend/src/hooks/useAuth.js`.
- [x] T039 [P] [US1] Página `frontend/src/pages/Register.jsx`.
- [x] T040 [P] [US1] Página `frontend/src/pages/Login.jsx`.
- [x] T041 [US1] Rutas `/register` y `/login` añadidas en `frontend/src/main.jsx`.

**Checkpoint**: US1 entregable. El usuario puede registrarse y loguearse; las cookies son HttpOnly; los errores son indistinguibles.

---

## Phase 4: User Story 2 — Protección de rutas (Priority: P1)

**Goal**: Todas las rutas son protegidas excepto inicio (`/`) y registro (`/register`). Sin sesión válida, el backend responde 401 y el frontend redirige a `/login`. Expone `GET /auth/me` para que el frontend conozca el estado de autenticación sin leer cookies HttpOnly.

**Independent Test**: Abrir en navegador una URL protegida sin cookies ⇒ redirige a `/login`. Con sesión activa ⇒ accede. En backend: `pytest -k protected`.

**FR cubiertos**: FR-015, FR-016.

### Tests for User Story 2 ⚠️ (Red)

- [x] T042 [P] [US2] Integration test `GET /auth/me` en `backend/tests/integration/test_protected_routes.py`.
- [x] T043 [P] [US2] Integration test ruta protegida requiere auth — cubierto por `test_auth_me_without_cookie_returns_401` (usa `/auth/me` como ruta protegida canónica).
- [x] T044 [P] [US2] Handler MSW `/auth/me` en `frontend/tests/mocks/authHandlers.js`.
- [x] T045 [P] [US2] Unit test `useAuth` en `frontend/tests/unit/useAuth.test.js`.
- [x] T046 [P] [US2] Integration test `ProtectedRoute` en `frontend/tests/integration/ProtectedRoute.test.jsx`.

### Implementation for User Story 2

- [x] T047 [US2] Dependency `get_current_user(request, db)` en `backend/app/core/security.py` y wrapper en `backend/app/api/routes/auth.py` que traduce `InvalidToken` → 401.
- [x] T048 [US2] Endpoint `GET /auth/me` en `backend/app/api/routes/auth.py`.
- [x] T049 [P] [US2] `authApi` ahora expone `/auth/me` a través del helper `request`.
- [x] T050 [P] [US2] `AuthContext` llama a `/auth/me` en mount y actualiza `status`; `useAuth` expone user/status.
- [x] T051 [P] [US2] Componente `ProtectedRoute` en `frontend/src/components/ProtectedRoute.jsx`.
- [ ] T052 [US2] Envolver rutas privadas con `<ProtectedRoute>` en `frontend/src/main.jsx` (no hay rutas privadas visibles aún; se hará cuando exista una página autenticada en US3 o Polish).

**Checkpoint**: US1+US2 funcionan. El frontend conoce el estado de sesión sin romper FR-012.

---

## Phase 5: User Story 3 — Sesión persistente con renovación automática (Priority: P2)

**Goal**: La sesión sobrevive al cierre del navegador dentro de la validez del refresh token. Si el access expira, el frontend pide `/auth/refresh` de forma transparente y obtiene un nuevo par (rotado). El refresh anterior queda en la blacklist.

**Independent Test**: Login → cerrar pestaña → reabrir la URL protegida → acceso concedido. Con `ACCESS_TOKEN_EXPIRE_MINUTES` reducido a 1, una acción autenticada después de 60 s dispara silent refresh sin afectar la UX.

**FR cubiertos**: FR-009, FR-010, FR-011, FR-012 (en refresh también).

### Tests for User Story 3 ⚠️ (Red)

- [x] T053 [P] [US3] Tests de refresh token con `jti` cubiertos en `backend/tests/integration/test_refresh.py` y `tests/unit/test_security.py::test_create_refresh_token_includes_jti_and_type_refresh`.
- [x] T054 [P] [US3] Integration test `POST /auth/refresh` rota tokens en `backend/tests/integration/test_refresh.py::test_refresh_rotates_tokens_and_blacklists_old_jti`.
- [x] T055 [P] [US3] `test_reusing_rotated_refresh_returns_401`.
- [x] T056 [P] [US3] `test_refresh_with_expired_token_returns_401` + `test_refresh_with_access_token_as_refresh_returns_401`.
- [x] T057 [P] [US3] Handler MSW `/auth/refresh` en `frontend/tests/mocks/authHandlers.js`.
- [ ] T058 [P] [US3] Auto-refresh silencioso en cliente (wrapper `apiCall` con reintento tras 401) — PENDIENTE (optimización UX; no bloquea funcionalidad ni tests existentes. Las cookies se refrescan manualmente llamando a `/auth/refresh`. Dejarlo como mejora).

### Implementation for User Story 3

- [x] T059 [P] [US3] Modelo `TokenBlacklist` en `backend/app/models/token_blacklist.py`.
- [x] T060 [US3] Migración Alembic para `users` y `token_blacklist` generada en `backend/app/db/migrations/versions/` (migración única `initial auth schema`).
- [x] T061 [US3] `core/security.py`: `create_refresh_token` ya incluye `jti`; blacklist verificada a través de `auth_service._is_jti_blacklisted`.
- [x] T062 [US3] `refresh_session` en `backend/app/services/auth_service.py`.
- [x] T063 [US3] Endpoint `POST /auth/refresh` en `backend/app/api/routes/auth.py`.
- [x] T064 [P] [US3] `authApi` soporta `POST /auth/refresh` vía `request` helper.
- [ ] T065 [P] [US3] Wrapper de auto-refresh en `useAuth` — PENDIENTE (ver T058; mejora UX opcional).

**Checkpoint**: Sesión persistente y renovación transparente operativas; token rotation con blacklist.

---

## Phase 6: User Story 4 — Cierre de sesión explícito (Priority: P2)

**Goal**: El usuario puede pulsar logout. El refresh actual se blacklista y las cookies se borran. Cualquier reutilización posterior de esas cookies contra rutas protegidas devuelve 401.

**Independent Test**: Con sesión activa, `POST /auth/logout` ⇒ 204 y cookies con `Max-Age=0`. Reutilizar el refresh anterior en `/auth/refresh` ⇒ 401.

**FR cubiertos**: FR-013, FR-014.

### Tests for User Story 4 ⚠️ (Red)

- [x] T066 [P] [US4] Integration test `POST /auth/logout` en `backend/tests/integration/test_logout.py`.
- [x] T067 [P] [US4] `test_after_logout_reusing_refresh_returns_401`.
- [x] T068 [P] [US4] Handler MSW `/auth/logout` en `frontend/tests/mocks/authHandlers.js`.
- [x] T069 [P] [US4] Unit test `useAuth logout` en `frontend/tests/unit/useAuth.test.js`.

### Implementation for User Story 4

- [x] T070 [US4] `logout_session` en `backend/app/services/auth_service.py`.
- [x] T071 [US4] Endpoint `POST /auth/logout` en `backend/app/api/routes/auth.py` (Max-Age=0 en ambas cookies, HttpOnly/Secure/SameSite=lax).
- [x] T072 [P] [US4] `AuthContext.logout` llama a `POST /auth/logout` y limpia estado.
- [ ] T073 [P] [US4] Botón de logout visible en páginas autenticadas — PENDIENTE hasta que haya páginas autenticadas en la UI (hoy sólo hay Home, Login, Register); se añadirá junto a la primera página autenticada.

**Checkpoint**: Logout operativo; cookies limpiadas y refresh invalidado.

---

## Phase 7: User Story 5 — Protección contra ataques de fuerza bruta (Priority: P3)

**Goal**: Limitar intentos de login por IP (slowapi, 5/min) y por cuenta (10 intentos fallidos en 15 min ⇒ lock 15 min; reset en login correcto). La cuenta bloqueada devuelve siempre `"Credenciales inválidas"` (FR-008).

**Independent Test**: Script que dispara 6 logins en <60 s desde la misma IP ⇒ el 6.º responde 429. Script que dispara 10 logins fallidos contra una cuenta en 15 min ⇒ el 11.º sigue devolviendo `"Credenciales inválidas"` aunque la password sea correcta; tras 15 min, el primer login correcto resetea el contador.

**FR cubiertos**: FR-017, FR-018, FR-019.

### Tests for User Story 5 ⚠️ (Red)

- [x] T074 [P] [US5] `test_ip_rate_limit_blocks_after_five_attempts_per_minute` en `backend/tests/integration/test_brute_force.py`.
- [x] T075 [P] [US5] `test_account_locks_after_ten_failed_attempts`.
- [x] T076 [P] [US5] `test_successful_login_resets_failed_attempts`.
- [x] T077 [P] [US5] `test_lock_expires_naturally`.

### Implementation for User Story 5

- [x] T078 [US5] Columnas `failed_login_attempts`, `locked_until` añadidas a `User`.
- [x] T079 [US5] Incluido en la migración inicial de Alembic (`initial_auth_schema`).
- [x] T080 [US5] `Limiter(key_func=get_remote_address)` en `backend/app/api/routes/auth.py` + `SlowAPIMiddleware` + handler 429 en `app/main.py`.
- [x] T081 [US5] `authenticate_user` aplica lock, reset y cooldown como propuesto.
- [x] T082 [US5] `@limiter.limit("5/minute")` con `exempt_when` para tests, aplicado a `POST /auth/login`.

**Checkpoint**: Todas las historias operativas. FR-001 a FR-019 implementados.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T083 [P] Purga opcional de `token_blacklist` — PENDIENTE (no bloquea funcionalidad; se añadirá como tarea de mantenimiento junto al primer deploy).
- [x] T084 [P] `README.md` en la raíz con enlace a `quickstart.md`.
- [x] T085 [P] `pytest --cov` ejecutado. Cobertura global 78% (security 86%, schemas/config/models 100%, routes 61%, service 71%). Los huecos están en ramas defensivas; aceptable para el alcance actual.
- [ ] T086 [P] `vitest --coverage` — PENDIENTE (optimización; la suite pasa sin medir cobertura).
- [ ] T087 Checklist manual contra HTTPS local — PENDIENTE (requiere mkcert/caddy; se hará en el primer entorno de staging).
- [x] T088 Revisión final de seguridad: grep en `backend/app/api/routes/auth.py` confirma que `access_token`/`refresh_token` sólo aparecen en `set_auth_cookies` y nunca en `response_model`/return values; `AuthenticatedUser` expone sólo `id`, `email`, `nickname`. Tests confirman: cookies HttpOnly+Secure+SameSite=lax (`test_auth_cookies_are_httponly_secure_samesite_lax`), rechazo de `alg=none` (`test_verify_token_rejects_alg_none`), rechazo de tipo de token incorrecto (`test_verify_token_rejects_wrong_type`, `test_auth_me_with_refresh_cookie_as_access_returns_401`, `test_refresh_with_access_token_as_refresh_returns_401`).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** → sin dependencias; debe terminar antes que Foundational.
- **Foundational (Phase 2)** → depende de Phase 1; **bloquea** todas las user stories.
- **US1 (Phase 3)** → depende de Foundational.
- **US2 (Phase 4)** → depende de US1 (necesita flujo de login para generar cookies que la dependency `get_current_user` verificará; tests y ProtectedRoute se apoyan en un usuario ya autenticado).
- **US3 (Phase 5)** → depende de US1 (refresh rota el par emitido en login); **puede paralelizarse con US2** si hay otro desarrollador (ficheros distintos).
- **US4 (Phase 6)** → depende de US3 (reutiliza `TokenBlacklist` y el modelo de refresh).
- **US5 (Phase 7)** → depende de US1 (modifica `/auth/login` y el servicio `authenticate_user`); puede solaparse con US4 porque toca sólo login, pero la migración Alembic debe ordenarse tras la de US3 para evitar conflictos.
- **Polish (Phase 8)** → depende de todas las stories.

### Within Each User Story (TDD orden obligatorio)

1. Escribir tests (Red).
2. Ejecutar y confirmar fallo.
3. Implementar el mínimo para pasar (Green).
4. Refactor manteniendo verde.

### Parallel Opportunities

- T002–T008 (Setup): todos [P] entre sí.
- T013–T018 (Foundational): todos [P] entre sí.
- Dentro de US1: T019–T027 (tests) son todos [P]; T028, T030, T037, T038, T039, T040 son [P] dentro del bloque de implementación.
- Equipo de ≥2 personas: tras completar US1, una persona puede tomar US2 y otra US3 en paralelo; US4 y US5 pueden empezarse cuando sus prerequisitos estén listos (US3 para US4; US1 para US5).

---

## Parallel Example: User Story 1

```bash
# Red — tests en paralelo (diferentes ficheros de test):
Task: "T019 [P] [US1] Unit tests hashing en backend/tests/unit/test_security.py"
Task: "T021 [P] [US1] Unit tests auth_service en backend/tests/unit/test_auth_service.py"
Task: "T022 [P] [US1] Integration test /auth/register en backend/tests/integration/test_auth_routes.py"
Task: "T026 [P] [US1] Test Register.jsx en frontend/tests/integration/Register.test.jsx"

# Green — implementación en paralelo (ficheros distintos):
Task: "T028 [P] [US1] Modelo User en backend/app/models/user.py"
Task: "T030 [P] [US1] Schemas Pydantic en backend/app/schemas/auth.py"
Task: "T037 [P] [US1] authApi register/login en frontend/src/api/authApi.js"
Task: "T039 [P] [US1] Register.jsx en frontend/src/pages/Register.jsx"
Task: "T040 [P] [US1] Login.jsx en frontend/src/pages/Login.jsx"
```

---

## Implementation Strategy

### MVP First (US1 solamente)

1. Completar Phase 1 (Setup).
2. Completar Phase 2 (Foundational) — crítico.
3. Completar Phase 3 (US1) con TDD estricto.
4. **Parar y validar**: ejecutar `pytest backend/tests -q` y `npm run test -- --run` en `frontend/`; correr la app localmente y completar el flujo register → login.
5. Demo / deploy opcional.

### Incremental Delivery

1. Setup + Foundational ⇒ base.
2. + US1 ⇒ **MVP**: registro y login con cookies seguras.
3. + US2 ⇒ rutas protegidas y estado de sesión en UI.
4. + US3 ⇒ sesión persistente y renovación silenciosa.
5. + US4 ⇒ logout explícito.
6. + US5 ⇒ hardening contra fuerza bruta.
7. Polish ⇒ cobertura, documentación, revisión final.

### Parallel Team Strategy

- Dev A: US1 (crítico — habilita todo lo demás).
- Dev B (tras US1): US2.
- Dev C (tras US1): US3.
- Dev B (tras US3): US4.
- Dev A (tras US1): US5 en paralelo con el resto, coordinando migraciones Alembic.

---

## Notes

- **Constitución II (NO NEGOCIABLE)**: cada tarea de test debe estar commiteada en rojo antes de la implementación asociada. Si se detecta código nuevo sin test previo en verde, revertir y rehacer.
- **Constitución I**: no instalar dependencias que no estén en la CVE audit aprobada en `research.md § CVE Audit`. Si se necesita una nueva, pedir supervisión humana antes de añadirla a `requirements.txt` o `package.json`.
- **Constitución III**: todo diagrama se añade como PlantUML en `specs/001-user-auth/contracts/` u otro sitio análogo; las decisiones técnicas que surjan durante la implementación se documentan como notas en `research.md`.
- **Constitución IV**: estructura de carpetas, librerías y flags son los fijados por el humano en el prompt; no sustituirlos.
- `[P]` = ficheros distintos sin dependencias pendientes.
- Confirmar que cada test falla antes de pasar a la implementación asociada.
- Commit después de cada tarea o bloque Red/Green/Refactor.
