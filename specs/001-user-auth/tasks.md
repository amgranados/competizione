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

- [ ] T001 Crear estructura de directorios del repositorio: `backend/app/{api/routes,core,db/migrations,models,schemas,services}`, `backend/tests/{unit,integration}`, `frontend/src/{api,context,hooks,components,pages}`, `frontend/tests/{mocks,unit,integration}` (sin ficheros dentro todavía salvo `.gitkeep` donde hiciera falta).
- [ ] T002 [P] Crear `backend/requirements.txt` con pins mínimos aprobados: `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]>=2.0.30`, `alembic>=1.13`, `asyncpg`, `pydantic>=2.7`, `pydantic-settings>=2.2`, `PyJWT>=2.9`, `passlib[bcrypt]>=1.7.4`, `python-multipart>=0.0.9`, `slowapi>=0.1.9`, `httpx`, `pytest`, `pytest-asyncio`, `pytest-cov`.
- [ ] T003 [P] Crear `frontend/package.json` con pins mínimos aprobados: `react@^18.3`, `react-dom@^18.3`, `react-router-dom@^6.22`, `vite@^5.2` (devDep), `vitest@^1.6` (devDep), `@testing-library/react`, `@testing-library/user-event`, `msw@^2`.
- [ ] T004 [P] Crear `backend/pyproject.toml` (o `pytest.ini`) con config de pytest: `asyncio_mode = "auto"`, `testpaths = ["tests"]`, `addopts = "--cov=app --cov-report=term-missing"`.
- [ ] T005 [P] Crear `frontend/vite.config.js` con plugin de React y `frontend/vitest.config.js` (o sección `test` en `vite.config.js`) apuntando a `tests/setup.js`.
- [ ] T006 [P] Crear `backend/.env.example` con variables: `DATABASE_URL`, `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES=15`, `REFRESH_TOKEN_EXPIRE_DAYS=7`, `FRONTEND_ORIGIN=http://localhost:5173`.
- [ ] T007 [P] Crear `frontend/.env.example` con `VITE_API_BASE_URL=http://localhost:8000`.
- [ ] T008 [P] Añadir entradas a `.gitignore` raíz: `backend/.venv/`, `backend/.env`, `backend/__pycache__/`, `backend/.pytest_cache/`, `backend/htmlcov/`, `frontend/node_modules/`, `frontend/.env.local`, `frontend/dist/`, `frontend/coverage/`.

**Checkpoint**: Estructura y archivos de configuración listos; dependencias declaradas (sin instalar todavía).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestructura que todas las historias usan. **Bloquea** el inicio de cualquier user story.

- [ ] T009 Implementar `Settings` con pydantic-settings (carga de `.env`, tipos: `DATABASE_URL: PostgresDsn`, `SECRET_KEY: str con min_length=32`, `ACCESS_TOKEN_EXPIRE_MINUTES: int`, `REFRESH_TOKEN_EXPIRE_DAYS: int`, `FRONTEND_ORIGIN: AnyHttpUrl`) en `backend/app/core/config.py`.
- [ ] T010 Implementar engine async y `AsyncSessionLocal` + `get_db()` dependency en `backend/app/db/base.py` (usa `settings.DATABASE_URL`).
- [ ] T011 Inicializar Alembic en `backend/app/db/migrations/` (`alembic init --template=async app/db/migrations`), configurar `alembic.ini` y `env.py` para leer `DATABASE_URL` desde `Settings` y apuntar a los modelos (`Base.metadata`).
- [ ] T012 Crear app FastAPI en `backend/app/main.py` con `CORSMiddleware(allow_origins=[settings.FRONTEND_ORIGIN], allow_credentials=True, allow_methods=["GET","POST"], allow_headers=["Content-Type"])`. Aún no registra rutas de auth.
- [ ] T013 [P] Crear fixtures de test en `backend/tests/conftest.py`: engine/sesión sobre BBDD de test (p. ej. base dedicada o SQLite async sólo si el humano acepta; si no, usar PostgreSQL de test vía `DATABASE_URL` override), `async_client` con `httpx.AsyncClient(app=app, base_url="http://test")`, fixture `db_session` con rollback por test.
- [ ] T014 [P] Crear `frontend/tests/setup.js` con arranque/stop de MSW (`beforeAll server.listen`, `afterEach server.resetHandlers`, `afterAll server.close`) y configuración global de Testing Library.
- [ ] T015 [P] Crear esqueleto de handlers MSW en `frontend/tests/mocks/authHandlers.js` y exportación de `server` (p. ej. en `frontend/tests/mocks/server.js`).
- [ ] T016 [P] Crear `frontend/index.html` y `frontend/src/main.jsx` con `<BrowserRouter>` envolviendo la app (sin rutas todavía).
- [ ] T017 [P] Crear `frontend/src/api/authApi.js` con helper base `request(path, options)` que hace `fetch(\`${import.meta.env.VITE_API_BASE_URL}${path}\`, { credentials: "include", headers: { "Content-Type": "application/json" }, ...options })` y parsea JSON. Aún sin endpoints específicos.
- [ ] T018 [P] Crear esqueleto de `frontend/src/context/AuthContext.jsx` con un provider que expone `{ user, status }` y funciones placeholder; y `frontend/src/hooks/useAuth.js` que lee el contexto. Sin llamadas a red todavía.

**Checkpoint**: Base lista. A partir de aquí, US1 puede empezar; US2–US5 dependen de US1 para el contrato de login/cookies.

---

## Phase 3: User Story 1 — Registro e inicio de sesión (Priority: P1) 🎯 MVP

**Goal**: Un visitante puede crear una cuenta (email + password, nickname opcional auto-generado `user<5-dígitos>`) e iniciar sesión; el servidor emite las cookies `access_token` y `refresh_token` como HttpOnly + Secure + SameSite=lax; errores de login son indistinguibles (mismo mensaje, código y timing).

**Independent Test**: Desde la UI, registrar un usuario nuevo, cerrar la pestaña y volver a entrar con esas credenciales. En el backend, `pytest backend/tests -k "register or login"` pasa en verde.

**FR cubiertos**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, FR-012 (HttpOnly en las cookies emitidas aquí).

### Tests for User Story 1 ⚠️ (Red: deben fallar antes de implementar)

- [ ] T019 [P] [US1] Tests unitarios de password hashing en `backend/tests/unit/test_security.py`: `hash_password` devuelve derivado ≠ plaintext, `verify_password` acepta el correcto y rechaza el incorrecto, `dummy_verify` se ejecuta en tiempo comparable.
- [ ] T020 [P] [US1] Tests unitarios de JWT con PyJWT en `backend/tests/unit/test_security.py`: `create_access_token`/`create_refresh_token` emiten tokens HS256 verificables, `verify_token` rechaza `alg=none` y algoritmos no permitidos.
- [ ] T021 [P] [US1] Tests unitarios en `backend/tests/unit/test_auth_service.py`: `generate_unique_nickname` devuelve formato `user\d{5}` y reintenta al colisionar; `register_user` persiste `User` con `password_hash`; duplicado de email y de nickname elevan `IntegrityError` capturable.
- [ ] T022 [P] [US1] Integration test `POST /auth/register` en `backend/tests/integration/test_auth_routes.py`: 201 + dos `Set-Cookie` con flags `HttpOnly; Secure; SameSite=lax`; 409 al repetir email; 409 al repetir nickname; 201 sin nickname ⇒ respuesta incluye `nickname` con regex `^user\d{5}$`.
- [ ] T023 [P] [US1] Integration test `POST /auth/login` en `backend/tests/integration/test_auth_routes.py`: credenciales correctas ⇒ 200 + cookies; credenciales incorrectas ⇒ 401 con `{"detail":"Credenciales inválidas"}`; email inexistente ⇒ misma respuesta exacta que contraseña incorrecta; diferencia de latencia entre ambos casos < umbral razonable (p. ej. 50 ms) promediando N intentos (verifica SC-003).
- [ ] T024 [P] [US1] Integration test cookies HttpOnly en `backend/tests/integration/test_auth_routes.py::test_tokens_are_httponly_secure_samesite_lax`: inspecciona cabeceras `Set-Cookie` del register y del login y comprueba los tres flags (verifica FR-012).
- [ ] T025 [P] [US1] Handlers MSW para `/auth/register` y `/auth/login` en `frontend/tests/mocks/authHandlers.js` (respuesta OK y respuesta 401 con `{"detail":"Credenciales inválidas"}`).
- [ ] T026 [P] [US1] Frontend integration test `Register.jsx` en `frontend/tests/integration/Register.test.jsx`: rellenar formulario + enviar ⇒ llama a `authApi.register`, redirige a zona autenticada; email duplicado muestra error 409.
- [ ] T027 [P] [US1] Frontend integration test `Login.jsx` en `frontend/tests/integration/Login.test.jsx`: credenciales correctas ⇒ llama a `authApi.login`, redirige; credenciales incorrectas ⇒ muestra exactamente `"Credenciales inválidas"`.

### Implementation for User Story 1

- [ ] T028 [P] [US1] Modelo `User` (id UUIDv4 PK, email unique-indexed, nickname unique-indexed, password_hash, created_at) en `backend/app/models/user.py`. **NO** incluir `failed_login_attempts`/`locked_until` todavía — se añaden en US5.
- [ ] T029 [US1] Primera migración Alembic autogenerada para tabla `users` en `backend/app/db/migrations/versions/` (depende de T028).
- [ ] T030 [P] [US1] Schemas Pydantic `RegisterRequest`, `LoginRequest`, `AuthenticatedUser`, `ErrorResponse` en `backend/app/schemas/auth.py` (reglas de `data-model.md` y `contracts/auth.openapi.yaml`).
- [ ] T031 [US1] `core/security.py` en `backend/app/core/security.py`: `CryptContext` con bcrypt; `hash_password`, `verify_password`, `dummy_verify` (precomputa un hash bcrypt y verifica contra una contraseña vacía para igualar latencia); `create_access_token`, `create_refresh_token` con PyJWT HS256 (claims `sub=user_id`, `exp`, `iat`, `type` ∈ {access, refresh}); `verify_token(token, expected_type)` con `algorithms=["HS256"]` estricto.
- [ ] T032 [US1] `services/auth_service.py` en `backend/app/services/auth_service.py`: `generate_unique_nickname(db)` (intenta hasta 10 veces `user<randint(10000,99999)>` hasta que no colisione), `register_user(db, payload)` (genera nickname si ausente, hashea password, inserta capturando `IntegrityError`), `authenticate_user(db, email, password)` (selecciona usuario; si no existe, ejecuta `dummy_verify` y levanta `InvalidCredentials`; si existe, verifica password; devuelve `User` o levanta `InvalidCredentials`).
- [ ] T033 [US1] Helper `set_auth_cookies(response, access_token, refresh_token)` en `backend/app/api/routes/auth.py` que añade ambas cookies con `httponly=True, secure=True, samesite="lax", max_age=exp_seconds, path="/"`.
- [ ] T034 [US1] Endpoint `POST /auth/register` en `backend/app/api/routes/auth.py`: valida `RegisterRequest`, llama `register_user`, emite access+refresh, llama `set_auth_cookies`, devuelve `AuthenticatedUser` con 201. Sobre `IntegrityError` responde 409 con mensaje específico (email/nickname).
- [ ] T035 [US1] Endpoint `POST /auth/login` en `backend/app/api/routes/auth.py`: valida `LoginRequest`, llama `authenticate_user`; en caso de `InvalidCredentials`, responde 401 con `{"detail":"Credenciales inválidas"}`; en caso de éxito, emite tokens y setea cookies; devuelve `AuthenticatedUser` con 200.
- [ ] T036 [US1] Registrar `auth_router` en `backend/app/main.py` (depende de T034, T035).
- [ ] T037 [P] [US1] `authApi.register(payload)` y `authApi.login(payload)` en `frontend/src/api/authApi.js`, usando el helper `request` (siempre `credentials: "include"`; el servidor pone las cookies).
- [ ] T038 [P] [US1] Extender `AuthContext`/`useAuth` en `frontend/src/context/AuthContext.jsx` y `frontend/src/hooks/useAuth.js` con acciones `register` y `login` que llaman a la API y marcan `status = "authenticated"` en éxito.
- [ ] T039 [P] [US1] Página `frontend/src/pages/Register.jsx` con formulario (email, password, nickname opcional) y manejo de errores 409/422.
- [ ] T040 [P] [US1] Página `frontend/src/pages/Login.jsx` con formulario (email, password) y manejo del error genérico.
- [ ] T041 [US1] Añadir rutas `/register` y `/login` en `frontend/src/main.jsx` (sin guardia todavía — eso es US2).

**Checkpoint**: US1 entregable. El usuario puede registrarse y loguearse; las cookies son HttpOnly; los errores son indistinguibles.

---

## Phase 4: User Story 2 — Protección de rutas (Priority: P1)

**Goal**: Todas las rutas son protegidas excepto inicio (`/`) y registro (`/register`). Sin sesión válida, el backend responde 401 y el frontend redirige a `/login`. Expone `GET /auth/me` para que el frontend conozca el estado de autenticación sin leer cookies HttpOnly.

**Independent Test**: Abrir en navegador una URL protegida sin cookies ⇒ redirige a `/login`. Con sesión activa ⇒ accede. En backend: `pytest -k protected`.

**FR cubiertos**: FR-015, FR-016.

### Tests for User Story 2 ⚠️ (Red)

- [ ] T042 [P] [US2] Integration test `GET /auth/me` en `backend/tests/integration/test_auth_routes.py`: con cookie válida ⇒ 200 con `AuthenticatedUser`; sin cookie ⇒ 401; con cookie de access caducada ⇒ 401.
- [ ] T043 [P] [US2] Integration test ruta protegida cualquiera requiere auth en `backend/tests/integration/test_auth_routes.py::test_protected_route_requires_authentication` (usa una ruta dummy montada sólo durante el test o el propio `/auth/me`).
- [ ] T044 [P] [US2] Handler MSW `/auth/me` en `frontend/tests/mocks/authHandlers.js` (200 con user y 401 según estado simulado).
- [ ] T045 [P] [US2] Unit test `useAuth` en `frontend/tests/unit/useAuth.test.js`: tras montar el provider, llama a `/auth/me`; si 200, `status === "authenticated"`; si 401, `status === "anonymous"`.
- [ ] T046 [P] [US2] Integration test `ProtectedRoute` en `frontend/tests/integration/ProtectedRoute.test.jsx`: renderiza `<ProtectedRoute>` en estado anonymous ⇒ redirige a `/login`; en estado authenticated ⇒ renderiza children.

### Implementation for User Story 2

- [ ] T047 [US2] Dependency `get_current_user(request, db)` en `backend/app/core/security.py`: lee `request.cookies["access_token"]`, verifica con `verify_token(token, expected_type="access")`, carga el `User` por `sub`; si falla cualquier paso, lanza `HTTPException(401, "Credenciales inválidas")`.
- [ ] T048 [US2] Endpoint `GET /auth/me` en `backend/app/api/routes/auth.py` que usa `Depends(get_current_user)` y devuelve `AuthenticatedUser` con 200.
- [ ] T049 [P] [US2] `authApi.me()` en `frontend/src/api/authApi.js`.
- [ ] T050 [P] [US2] Extender `AuthContext`/`useAuth` en `frontend/src/context/AuthContext.jsx` y `frontend/src/hooks/useAuth.js`: al montar el provider, llamar `authApi.me()`; actualizar `status` a `"authenticated"|"anonymous"`; exponer user actual.
- [ ] T051 [P] [US2] Componente `ProtectedRoute` en `frontend/src/components/ProtectedRoute.jsx` que redirige a `/login` si `status === "anonymous"`; mientras `status === "loading"`, muestra un placeholder.
- [ ] T052 [US2] Envolver rutas privadas con `<ProtectedRoute>` en `frontend/src/main.jsx` y dejar `/` y `/register` públicas (cumple FR-015).

**Checkpoint**: US1+US2 funcionan. El frontend conoce el estado de sesión sin romper FR-012.

---

## Phase 5: User Story 3 — Sesión persistente con renovación automática (Priority: P2)

**Goal**: La sesión sobrevive al cierre del navegador dentro de la validez del refresh token. Si el access expira, el frontend pide `/auth/refresh` de forma transparente y obtiene un nuevo par (rotado). El refresh anterior queda en la blacklist.

**Independent Test**: Login → cerrar pestaña → reabrir la URL protegida → acceso concedido. Con `ACCESS_TOKEN_EXPIRE_MINUTES` reducido a 1, una acción autenticada después de 60 s dispara silent refresh sin afectar la UX.

**FR cubiertos**: FR-009, FR-010, FR-011, FR-012 (en refresh también).

### Tests for User Story 3 ⚠️ (Red)

- [ ] T053 [P] [US3] Tests unitarios en `backend/tests/unit/test_security.py`: `create_refresh_token` incluye claim `jti`; `verify_refresh_token_not_blacklisted(db, token)` rechaza `jti` presentes en `token_blacklist`.
- [ ] T054 [P] [US3] Integration test `POST /auth/refresh` rota tokens en `backend/tests/integration/test_auth_routes.py`: refresh válido ⇒ 200 + nuevas cookies; el `jti` del refresh anterior queda en `token_blacklist`.
- [ ] T055 [P] [US3] Integration test refresh reutilizado rechazado: un segundo `POST /auth/refresh` con el mismo refresh ya rotado ⇒ 401.
- [ ] T056 [P] [US3] Integration test refresh expirado rechazado: se emite un refresh con `exp` en el pasado (vía helper) ⇒ `POST /auth/refresh` ⇒ 401.
- [ ] T057 [P] [US3] Handler MSW `/auth/refresh` en `frontend/tests/mocks/authHandlers.js`.
- [ ] T058 [P] [US3] Unit test `useAuth` auto-refresh en `frontend/tests/unit/useAuth.test.js`: una llamada API que responde 401 ⇒ `useAuth` dispara `/auth/refresh` y reintenta; tras éxito, `status` sigue `"authenticated"`.

### Implementation for User Story 3

- [ ] T059 [P] [US3] Modelo `TokenBlacklist` (`jti: UUID PK`, `user_id: UUID FK users.id`, `revoked_at: datetime`, `expires_at: datetime`) en `backend/app/models/token_blacklist.py`.
- [ ] T060 [US3] Migración Alembic para `token_blacklist` en `backend/app/db/migrations/versions/` (depende de T059).
- [ ] T061 [US3] Actualizar `backend/app/core/security.py`: generar `jti = uuid4()` al crear refresh; añadir `is_refresh_blacklisted(db, jti) -> bool`; añadir `rotate_refresh_token(db, old_payload, user) -> (access, refresh)` que inserta en blacklist y emite un nuevo par.
- [ ] T062 [US3] En `backend/app/services/auth_service.py` añadir `refresh_session(db, refresh_cookie)`: valida token (tipo `refresh`, firma, exp), comprueba blacklist, llama `rotate_refresh_token`, devuelve nuevo par de tokens y el `User`.
- [ ] T063 [US3] Endpoint `POST /auth/refresh` en `backend/app/api/routes/auth.py`: lee cookie `refresh_token`; si ausente o inválido ⇒ 401; si ok, llama `refresh_session` y setea cookies nuevas con `set_auth_cookies`. Devuelve `AuthenticatedUser` con 200.
- [ ] T064 [P] [US3] `authApi.refresh()` en `frontend/src/api/authApi.js`.
- [ ] T065 [P] [US3] En `frontend/src/hooks/useAuth.js` añadir wrapper `apiCall` que intercepta 401 ⇒ llama `authApi.refresh()` ⇒ reintenta la petición original **una** vez; si refresh también falla, marca `status = "anonymous"` y redirige a `/login`.

**Checkpoint**: Sesión persistente y renovación transparente operativas; token rotation con blacklist.

---

## Phase 6: User Story 4 — Cierre de sesión explícito (Priority: P2)

**Goal**: El usuario puede pulsar logout. El refresh actual se blacklista y las cookies se borran. Cualquier reutilización posterior de esas cookies contra rutas protegidas devuelve 401.

**Independent Test**: Con sesión activa, `POST /auth/logout` ⇒ 204 y cookies con `Max-Age=0`. Reutilizar el refresh anterior en `/auth/refresh` ⇒ 401.

**FR cubiertos**: FR-013, FR-014.

### Tests for User Story 4 ⚠️ (Red)

- [ ] T066 [P] [US4] Integration test `POST /auth/logout` en `backend/tests/integration/test_auth_routes.py`: 204; dos cabeceras `Set-Cookie` con `Max-Age=0` para `access_token` y `refresh_token`; el `jti` del refresh usado queda en `token_blacklist`.
- [ ] T067 [P] [US4] Integration test tras logout el refresh reutilizado se rechaza en `POST /auth/refresh` ⇒ 401.
- [ ] T068 [P] [US4] Handler MSW `/auth/logout` en `frontend/tests/mocks/authHandlers.js`.
- [ ] T069 [P] [US4] Unit test `useAuth.logout` en `frontend/tests/unit/useAuth.test.js`: tras logout, `status === "anonymous"` y se redirige a `/login`.

### Implementation for User Story 4

- [ ] T070 [US4] En `backend/app/services/auth_service.py` añadir `logout(db, refresh_cookie)`: valida el refresh (si inválido, devuelve sin error — el objetivo es invalidar); si válido, inserta `jti` en `token_blacklist` con `expires_at` copiado.
- [ ] T071 [US4] Endpoint `POST /auth/logout` en `backend/app/api/routes/auth.py`: llama `logout`; añade cabeceras `Set-Cookie access_token=; Max-Age=0; Path=/; HttpOnly; Secure; SameSite=lax` y equivalente para `refresh_token`; responde 204.
- [ ] T072 [P] [US4] `authApi.logout()` en `frontend/src/api/authApi.js`.
- [ ] T073 [P] [US4] En `frontend/src/hooks/useAuth.js` añadir `logout()` que llama a la API, limpia el estado local y redirige a `/login`; añadir un botón de logout visible en las páginas autenticadas (p. ej. en un layout mínimo) en `frontend/src/pages/`.

**Checkpoint**: Logout operativo; cookies limpiadas y refresh invalidado.

---

## Phase 7: User Story 5 — Protección contra ataques de fuerza bruta (Priority: P3)

**Goal**: Limitar intentos de login por IP (slowapi, 5/min) y por cuenta (10 intentos fallidos en 15 min ⇒ lock 15 min; reset en login correcto). La cuenta bloqueada devuelve siempre `"Credenciales inválidas"` (FR-008).

**Independent Test**: Script que dispara 6 logins en <60 s desde la misma IP ⇒ el 6.º responde 429. Script que dispara 10 logins fallidos contra una cuenta en 15 min ⇒ el 11.º sigue devolviendo `"Credenciales inválidas"` aunque la password sea correcta; tras 15 min, el primer login correcto resetea el contador.

**FR cubiertos**: FR-017, FR-018, FR-019.

### Tests for User Story 5 ⚠️ (Red)

- [ ] T074 [P] [US5] Integration test IP rate limit en `backend/tests/integration/test_auth_routes.py::test_ip_rate_limit_returns_429_after_5_attempts_in_a_minute` (6 intentos rápidos ⇒ el 6.º devuelve 429).
- [ ] T075 [P] [US5] Integration test lock por cuenta en `backend/tests/integration/test_auth_routes.py::test_account_locks_after_10_failed_attempts_in_15_minutes` (el 11.º intento, incluso con password correcta, devuelve 401 `"Credenciales inválidas"`).
- [ ] T076 [P] [US5] Integration test reset de contador en `backend/tests/integration/test_auth_routes.py::test_successful_login_resets_failed_attempts_and_locked_until` (9 fallos + 1 éxito ⇒ `failed_login_attempts == 0` y `locked_until is null`).
- [ ] T077 [P] [US5] Integration test expiración del lock en `backend/tests/integration/test_auth_routes.py::test_lock_expires_after_window` (avanzar `locked_until` a pasado ⇒ próximo intento fallido reinicia la cuenta).

### Implementation for User Story 5

- [ ] T078 [US5] Añadir columnas `failed_login_attempts: int default 0` y `locked_until: datetime | null` al modelo `User` en `backend/app/models/user.py`.
- [ ] T079 [US5] Migración Alembic que añade esas dos columnas en `backend/app/db/migrations/versions/`.
- [ ] T080 [US5] Configurar `slowapi.Limiter(key_func=get_remote_address)` como singleton en `backend/app/core/security.py` (o en un módulo dedicado) y registrar el middleware/handler en `backend/app/main.py` (`app.state.limiter = limiter`, `app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)`).
- [ ] T081 [US5] Extender `authenticate_user` en `backend/app/services/auth_service.py`: si `locked_until > now` ⇒ levantar `InvalidCredentials` sin siquiera comparar password; en fallo ⇒ `failed_login_attempts += 1` y si supera 10 en los últimos 15 min ⇒ `locked_until = now + 15 min`; en éxito ⇒ `failed_login_attempts = 0`, `locked_until = None`.
- [ ] T082 [US5] Añadir decorador `@limiter.limit("5/minute")` al endpoint `POST /auth/login` en `backend/app/api/routes/auth.py` (depende de T080).

**Checkpoint**: Todas las historias operativas. FR-001 a FR-019 implementados.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T083 [P] Añadir tarea de purga opcional de `token_blacklist` (función `purge_expired_blacklist(db)` + documentación de cómo invocarla manualmente o vía cron) en `backend/app/services/auth_service.py`.
- [ ] T084 [P] Crear `README.md` en la raíz con enlace a `specs/001-user-auth/quickstart.md` y resumen del stack.
- [ ] T085 [P] Ejecutar `pytest --cov=app --cov-report=term-missing` en `backend/` y subir cobertura de `core/security.py`, `services/auth_service.py`, `api/routes/auth.py` por encima del 90%.
- [ ] T086 [P] Ejecutar `npm run test -- --coverage` en `frontend/` y verificar cobertura de `hooks/useAuth.js`, `context/AuthContext.jsx`, `components/ProtectedRoute.jsx`, `pages/Login.jsx`, `pages/Register.jsx`.
- [ ] T087 Ejecutar el checklist manual de `specs/001-user-auth/quickstart.md § Comprobación manual` contra un entorno local con HTTPS (mkcert/caddy) y anotar resultados.
- [ ] T088 Revisión final de seguridad: grep sobre `backend/app/` para verificar que ningún `response.json` devuelve tokens; verificar que todos los `set_cookie` usan `httponly=True, secure=True, samesite="lax"`; ejecutar test que intenta login con `alg=none` y confirma rechazo.

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
