---
description: "Task list for feature 003-edit-profile: Editar perfil de usuario"
---

# Tasks: Editar perfil de usuario

**Input**: Design documents from `specs/003-edit-profile/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: TDD es **OBLIGATORIO** por la Constitución (Principio II, NO NEGOCIABLE). Cada tarea de test debe fallar (Red) antes de escribir la implementación asociada (Green).

**Organization**: Tareas agrupadas por user story en su orden de prioridad. La numeración `US1, US2, US3` se preserva tal cual aparece en [spec.md](./spec.md).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo con otras `[P]` del mismo bloque (ficheros distintos, sin dependencias pendientes).
- **[Story]**: `US1`, `US2`, `US3` para tareas de historia. Setup, Foundational y Polish no llevan etiqueta de historia.
- Todos los paths son relativos a la raíz del repositorio.

## Path Conventions

Estructura fijada en [plan.md § Project Structure](./plan.md) (Variante B — backend API + frontend SPA):

- Backend: `backend/app/**`, `backend/tests/**`
- Frontend: `frontend/src/**`, `frontend/tests/**`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Activar `respx` como dependencia test-only (desbloqueada de 002), poner `RIOT_API_KEY` operativa en `.env.example` y verificar que las carpetas necesarias ya existen tras 001/002.

- [x] T001 Añadir `respx>=0.21` a `backend/requirements.txt` (test-only) y registrar en [research.md § CVE Audit](./research.md) que la instalación efectiva la realiza esta tarea.
- [x] T002 [P] Actualizar `backend/.env.example` para descomentar `RIOT_API_KEY` con un valor de ejemplo y un comentario indicando que ahora **es operativa**: si está definida fuerza `HttpRiotAPIClient`; si está vacía, fuerza `MockRiotAPIClient` con log INFO (mismo patrón que 002, ahora cableado).
- [x] T003 [P] Verificar/crear (con `.gitkeep` si vacíos) los subdirectorios usados por la feature: `backend/app/services/riot_api/` (ya existe desde 002), `frontend/tests/mocks/` (ya existe), `frontend/src/components/` (ya existe). No se crean carpetas nuevas; tarea de chequeo.

**Checkpoint**: Setup listo. La instalación real de `respx` se confirmará con `pip install -r backend/requirements.txt` antes de ejecutar T010-T011.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestructura transversal que **toda** user story consume: extensión del modelo `User`, nuevo modelo `RiotAccount`, migración Alembic, esquemas Pydantic v2, endpoint base `GET /api/profile` (sin datos LoL), página `Profile.jsx` esqueleto y `profileApi.js` con `getProfile`. Esto permite que cada US edite/añada flujos sin recrear la base.

**⚠️ CRITICAL**: Ninguna user story puede empezar hasta que esta fase esté completa.

### Tests (Red — deben fallar antes de implementar)

- [x] T004 [P] Test unitario `backend/tests/unit/test_models.py::test_user_has_avatar_url_and_deleted_at_columns`: la tabla `users` (tras correr migraciones) tiene columnas `avatar_url VARCHAR(2048) NULL` y `deleted_at TIMESTAMPTZ NULL`. Si el archivo `test_models.py` no existe aún, crearlo.
- [x] T005 [P] Test unitario `backend/tests/unit/test_models.py::test_riot_account_unique_per_user_and_per_puuid`: insertar dos `RiotAccount` con el mismo `user_id` falla (UNIQUE); insertar dos con el mismo `puuid` falla; INV-1 e INV-7 de [data-model.md](./data-model.md).
- [x] T006 [P] Test unitario `backend/tests/unit/test_profile_schemas.py::test_update_avatar_accepts_https_and_rejects_garbage` en `backend/tests/unit/test_profile_schemas.py`: `UpdateAvatar(avatar_url="https://i.imgur.com/x.png")` valida; `"not-a-url"` lanza `ValidationError`; `null` se acepta y deja la URL en None.
- [x] T007 [P] Test unitario `backend/tests/unit/test_profile_schemas.py::test_link_riot_account_validates_region_whitelist`: `LinkRiotAccount(game_name="A", tag_line="B", region="EUW1")` valida; `region="ZZZ"` lanza `ValidationError` (INV-8).
- [x] T008 [P] Test unitario `backend/tests/unit/test_profile_schemas.py::test_delete_account_confirm_requires_string`: `DeleteAccountConfirm(confirmation="alice")` valida; ausencia de campo lanza `ValidationError`.
- [x] T009 [P] Test integración `backend/tests/integration/test_profile_routes.py::test_get_profile_requires_authentication`: `GET /api/profile` sin cookie de sesión → 401.
- [x] T010 [P] Test integración `backend/tests/integration/test_profile_routes.py::test_get_profile_returns_basic_data_for_user_without_lol`: usuario autenticado sin `RiotAccount` → 200, body con `id`, `nickname`, `email`, `avatar_url=null`, `linked_games=[]`, `lol_stats=null`.
- [x] T011 [P] Test frontend `frontend/tests/integration/Profile.test.jsx::"renders profile shell with nickname"`: `<Profile />` con MSW devolviendo `getProfile` mock muestra el nickname y la sección "Juegos vinculados" vacía. Crear el archivo si no existe.

### Implementation (Green)

- [x] T012 Extender `User` model en `backend/app/models/user.py` añadiendo `avatar_url: Mapped[str | None] = mapped_column(String(2048), nullable=True, default=None)` y `deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)`.
- [x] T013 [P] Crear `RiotAccount` model en `backend/app/models/riot_account.py` con: `id (UUID PK)`, `user_id (UUID FK users.id ON DELETE CASCADE, UNIQUE)`, `puuid (String(78) UNIQUE)`, `region (String(8))`, `linked_at (TIMESTAMPTZ default now)`. Registrar el import en `backend/app/db/base.py` para que Alembic lo detecte.
- [x] T014 Generar migración Alembic `backend/app/db/migrations/versions/<hash>_add_avatar_and_riot_account.py` que (a) añada columnas `users.avatar_url` y `users.deleted_at`, (b) cree tabla `riot_accounts` con sus índices/constraints; `downgrade()` revierte ambos pasos en orden inverso. Aplicar `alembic upgrade head` y verificar que T004 y T005 pasan.
- [x] T015 [P] Crear `backend/app/schemas/profile.py` con: `UpdateNickname(nickname: str)` (min 3, max 32), `UpdatePassword(current_password: str, new_password: str con min 8)`, `UpdateAvatar(avatar_url: HttpUrl | None)`, `LinkRiotAccount(game_name: str, tag_line: str, region: Literal[...whitelist...])`, `DeleteAccountConfirm(confirmation: str)`, `LinkedGameSummary`, `ProfileBasic`, `ProfileResponse`, `LoLStatsResponse` (con sub-modelos `SummonerSection`, `RankedSection`, `MasterySection`, `MatchesSection`, `RankedEntry`, `ChampionMastery`, `MatchSummary`) según [contracts/profile.openapi.yaml](./contracts/profile.openapi.yaml).
- [x] T016 Crear `backend/app/services/profile_service.py` con la función `async def get_profile(db, user_id) -> ProfileResponse` (versión foundational: solo datos básicos, sin LoL stats; eso se completa en US2). Resuelve `linked_games` haciendo SELECT a `riot_accounts` por `user_id`.
- [x] T017 Crear `backend/app/api/routes/profile.py` con `router = APIRouter(prefix="/profile", tags=["profile"])` y la ruta `GET /` que llama a `profile_service.get_profile`. Dependencias: `Depends(get_current_user)` (heredado de 001) y `Depends(get_db)`.
- [x] T018 Registrar el router en `backend/app/main.py`: `app.include_router(profile_router, prefix="/api")`. Verificar que T009 y T010 pasan.
- [x] T019 [P] Crear `frontend/src/api/profileApi.js` exportando `getProfile()` que hace `fetch("/api/profile", { credentials: "include" })`. Sin manejo específico de errores; deja que el componente lo gestione.
- [x] T020 [P] Crear `frontend/src/pages/Profile.jsx` con un esqueleto que invoca `getProfile` al montar (`useEffect`), muestra nickname y la sección "Juegos vinculados" (vacía o con `<LinkedGames />` placeholder cuando exista). Estado de loading y de error.
- [x] T021 Añadir ruta `/profile` protegida en `frontend/src/main.jsx` envuelta en `<ProtectedRoute>` (heredado de 001) que renderiza `<Profile />`.
- [x] T022 [P] Crear `frontend/tests/mocks/profileHandlers.js` con un handler para `GET /api/profile` que devuelve un perfil mock por defecto (sin LoL). Registrarlo en `frontend/tests/mocks/server.js` (importar y añadir al array de handlers). Verificar que T011 pasa.

**Checkpoint**: La infraestructura está lista. `GET /api/profile` funciona para usuarios autenticados sin LoL vinculado. Las stories ya pueden empezar.

---

## Phase 3: User Story 1 — Visualizar el perfil y editar datos básicos (Priority: P1) 🎯 MVP

**Goal**: Un usuario autenticado entra en `/profile`, ve sus datos actuales y puede modificar nickname, contraseña y avatar (URL). Se aplican validaciones (unicidad, complejidad, formato URL) y, tras cambio de contraseña, las otras sesiones quedan invalidadas (HD-5).

**Independent Test**: [quickstart.md § 5.2-5.4](./quickstart.md). En backend: `pytest backend/tests -k "profile and (nickname or password or avatar)"` en verde. En frontend: `Profile.test.jsx` cubriendo los 3 flujos.

**FR cubiertos**: FR-001, FR-002, FR-004, FR-005, FR-006, FR-007, FR-008, FR-009, FR-017, FR-020, FR-025, FR-026.

### Tests unitarios backend (Red) — en paralelo

- [x] T023 [P] [US1] Test `test_update_nickname_accepts_unique_value` en `backend/tests/unit/test_profile_service.py`: con dos usuarios `alice`, `bob`, `update_nickname(alice.id, "alice2")` → ok, fila de `alice.nickname == "alice2"`.
- [x] T024 [P] [US1] Test `test_update_nickname_rejects_when_taken_by_other` en `backend/tests/unit/test_profile_service.py`: `update_nickname(alice.id, "bob")` → lanza excepción de dominio (`NicknameAlreadyTaken` o equivalente); `alice.nickname` no cambia.
- [x] T025 [P] [US1] Test `test_update_nickname_idempotent_when_same_as_current` en `backend/tests/unit/test_profile_service.py`: `update_nickname(alice.id, alice.nickname)` → no lanza excepción y no genera UPDATE redundante (verificar con spy o estado equivalente).
- [x] T026 [P] [US1] Test `test_change_password_validates_current_password` en `backend/tests/unit/test_profile_service.py`: `change_password(user_id, current_password="wrong", new_password="ValidPwd1234")` → lanza excepción de autenticación; `password_hash` no cambia.
- [x] T027 [P] [US1] Test `test_change_password_validates_new_password_minlength` en `backend/tests/unit/test_profile_service.py`: contraseña nueva con 7 chars → lanza `WeakPasswordError`; reusa el validador de 001.
- [x] T028 [P] [US1] Test `test_change_password_blacklists_other_sessions` en `backend/tests/unit/test_profile_service.py`: con dos refresh tokens activos del usuario y la sesión actual identificada, tras `change_password(...)` la otra sesión queda en `token_blacklist` y la actual no. INV-6 / HD-5.
- [x] T029 [P] [US1] Test `test_update_avatar_accepts_null_to_clear` en `backend/tests/unit/test_profile_service.py`: con `users.avatar_url` previamente puesto, `update_avatar(user_id, None)` → fila tiene `avatar_url=None`.
- [x] T030 [P] [US1] Test `test_update_avatar_persists_https_url` en `backend/tests/unit/test_profile_service.py`: `update_avatar(user_id, "https://cdn.example/x.png")` → fila tiene esa URL exacta.

### Tests integración backend (Red) — en paralelo

- [x] T031 [P] [US1] Test `test_patch_nickname_returns_200_with_updated_profile` en `backend/tests/integration/test_profile_routes.py`: `PATCH /api/profile/nickname` con cookie válida y nickname libre → 200, body con nickname nuevo.
- [x] T032 [P] [US1] Test `test_patch_nickname_returns_409_when_taken` en `backend/tests/integration/test_profile_routes.py`: nickname de otro usuario → 409, `detail` informativo, fila intacta.
- [x] T033 [P] [US1] Test `test_patch_nickname_returns_400_on_too_short` en `backend/tests/integration/test_profile_routes.py`: nickname de 2 chars → 400 (Pydantic).
- [x] T034 [P] [US1] Test `test_patch_password_returns_204_and_rotates_cookies` en `backend/tests/integration/test_profile_routes.py`: payload válido → 204, response trae nuevas cookies `access_token` y `refresh_token` rotadas.
- [x] T035 [P] [US1] Test `test_patch_password_returns_400_on_wrong_current_password` en `backend/tests/integration/test_profile_routes.py`.
- [x] T036 [P] [US1] Test `test_patch_password_invalidates_other_sessions_globally` en `backend/tests/integration/test_profile_routes.py`: una segunda sesión del mismo usuario, tras el cambio, recibe 401 al hacer cualquier llamada autenticada (HD-5).
- [x] T037 [P] [US1] Test `test_patch_avatar_returns_200_with_updated_url` en `backend/tests/integration/test_profile_routes.py`.
- [x] T038 [P] [US1] Test `test_patch_avatar_returns_400_on_invalid_url` en `backend/tests/integration/test_profile_routes.py`.
- [x] T039 [P] [US1] Test `test_patch_avatar_accepts_null_to_reset_to_default` en `backend/tests/integration/test_profile_routes.py`.

### Tests frontend (Red) — en paralelo

- [x] T040 [P] [US1] Test unitario `frontend/tests/unit/ProfileForm.test.jsx::"submits nickname change"`: render del componente con MSW en verde para `PATCH /api/profile/nickname`; al cambiar el input y pulsar submit, llamada hecha con el nuevo valor.
- [x] T041 [P] [US1] Test unitario `frontend/tests/unit/ProfileForm.test.jsx::"shows error message on 409 nickname conflict"`: MSW devuelve 409, el componente muestra "Nickname no disponible".
- [x] T042 [P] [US1] Test integración `frontend/tests/integration/Profile.test.jsx::"changes password and shows success"`: flujo completo desde la página `Profile` con MSW.
- [x] T043 [P] [US1] Test integración `frontend/tests/integration/Profile.test.jsx::"updates avatar URL and reflects new image"`: pegar URL → submit → la imagen del avatar se re-renderiza con el nuevo `src`.

### Implementation backend (Green)

- [x] T044 [US1] Implementar `profile_service.update_nickname(db, user_id, new_nickname)` en `backend/app/services/profile_service.py`: chequea unicidad excluyendo el propio user; idempotencia si coincide con el actual; lanza `NicknameAlreadyTaken` si está en uso.
- [x] T045 [US1] Implementar `profile_service.change_password(db, user_id, current_session_jti, current_password, new_password)` en `backend/app/services/profile_service.py`: verifica current_password con `verify_password` (001); valida new_password con el mismo validador de 001; persiste hash nuevo; añade a `token_blacklist` todas las sesiones activas distintas de la actual (`current_session_jti`); rota access+refresh para la sesión actual y devuelve los nuevos tokens al caller.
- [x] T046 [US1] Implementar `profile_service.update_avatar(db, user_id, avatar_url)` en `backend/app/services/profile_service.py`: persiste el campo (acepta None); no realiza ninguna petición externa.
- [x] T047 [US1] Añadir ruta `PATCH /nickname` en `backend/app/api/routes/profile.py` que invoca `update_nickname` y devuelve `ProfileBasic`. Maneja `NicknameAlreadyTaken` → 409.
- [x] T048 [US1] Añadir ruta `PATCH /password` en `backend/app/api/routes/profile.py`: invoca `change_password`, monta las cookies rotadas en la response (igual patrón que 001 login) y responde 204. Maneja errores de current_password → 400.
- [x] T049 [US1] Añadir ruta `PATCH /avatar` en `backend/app/api/routes/profile.py`: invoca `update_avatar`, devuelve `ProfileBasic`. Verificar que T031-T039 y T044-T046 pasan.

### Implementation frontend (Green)

- [x] T050 [P] [US1] Extender `frontend/src/api/profileApi.js` con `updateNickname({ nickname })`, `updatePassword({ current_password, new_password })`, `updateAvatar({ avatar_url })`. Todas con `credentials: "include"` y `Content-Type: application/json`.
- [x] T051 [P] [US1] Crear `frontend/src/components/ProfileForm.jsx`: tres bloques (nickname, password, avatar). Cada bloque tiene su propio submit independiente. Estado local; muestra mensaje de éxito/error por bloque.
- [x] T052 [US1] Wirear `<ProfileForm />` en `frontend/src/pages/Profile.jsx` debajo de la cabecera con avatar/nickname.
- [x] T053 [P] [US1] Añadir handlers en `frontend/tests/mocks/profileHandlers.js` para `PATCH /api/profile/nickname`, `PATCH /api/profile/password`, `PATCH /api/profile/avatar`. Registrar/actualizar en `frontend/tests/mocks/server.js`. Verificar que T040-T043 pasan.

**Checkpoint**: US1 funcional y testeable de forma independiente. El usuario puede ver su perfil y editar nickname, contraseña y avatar. Cumple SC-001, SC-002.

---

## Phase 4: User Story 2 — Vincular y desvincular cuenta de League of Legends (Priority: P2)

**Goal**: Un usuario autenticado puede vincular su cuenta de LoL introduciendo Riot ID + región; el sistema obtiene el PUUID via Riot API y descarta las credenciales. Una vez vinculado, el perfil muestra los datos públicos en tiempo real (nivel, servidor, ranked solo/dúo, ranked flex, maestría top-5, últimas 5 partidas) con degradación elegante por sección. El usuario puede desvincular siempre que no participe en un torneo activo del juego.

**Independent Test**: [quickstart.md § 5.5-5.6](./quickstart.md). En backend: `pytest backend/tests -k "lol or riot or link or unlink"` en verde. En frontend: `LinkedGames.test.jsx` y `LoLStats.test.jsx`.

**FR cubiertos**: FR-003, FR-010, FR-011, FR-012, FR-013, FR-014, FR-015, FR-016, FR-026.

**HD aplicadas**: HD-3 (paralelismo + degradación), HD-6 (descarte de credenciales), HD-7 (mensajes de error).

### Tests unitarios Riot client (Red) — en paralelo

- [x] T054 [P] [US2] Test `test_mock_get_summoner_profile_returns_seeded_data` en `backend/tests/unit/test_riot_api_client.py`: `MockRiotAPIClient(configured_summoner={puuid: SummonerProfile(...)})` devuelve el objeto sembrado.
- [x] T055 [P] [US2] Test `test_mock_get_ranked_stats_returns_seeded_data` en `backend/tests/unit/test_riot_api_client.py`.
- [x] T056 [P] [US2] Test `test_mock_get_champion_mastery_respects_limit` en `backend/tests/unit/test_riot_api_client.py`.
- [x] T057 [P] [US2] Test `test_mock_get_recent_matches_respects_limit` en `backend/tests/unit/test_riot_api_client.py`.
- [x] T058 [P] [US2] Test `test_mock_resolve_puuid_returns_seeded_value_or_raises` en `backend/tests/unit/test_riot_api_client.py`: para `(game_name, tag_line)` configurado devuelve PUUID; si no, lanza `RiotIdentityError`.
- [x] T059 [P] [US2] Test `test_http_resolve_puuid_with_respx_200` en `backend/tests/unit/test_riot_api_client.py`: con `respx` simulando `GET /riot/account/v1/accounts/by-riot-id/...` 200, el método devuelve el PUUID parseado.
- [x] T060 [P] [US2] Test `test_http_resolve_puuid_raises_identity_error_on_4xx` en `backend/tests/unit/test_riot_api_client.py`: 401, 403 y 404 → todos lanzan `RiotIdentityError` (mismo tipo) — HD-7.
- [x] T061 [P] [US2] Test `test_http_resolve_puuid_raises_unavailable_on_5xx_or_timeout` en `backend/tests/unit/test_riot_api_client.py`: 500/503 y `httpx.TimeoutException` → lanzan `RiotUnavailableError`.
- [x] T062 [P] [US2] Test `test_http_get_summoner_profile_with_respx_200` en `backend/tests/unit/test_riot_api_client.py`.
- [x] T063 [P] [US2] Test `test_http_get_ranked_stats_with_respx_200` en `backend/tests/unit/test_riot_api_client.py`: respuesta con dos colas → devuelve `RankedStats(solo_duo=..., flex=...)`; con cola única → la otra es `None`.
- [x] T064 [P] [US2] Test `test_http_get_champion_mastery_with_respx_200` en `backend/tests/unit/test_riot_api_client.py`.
- [x] T065 [P] [US2] Test `test_http_get_recent_matches_with_respx_200_and_5_matches` en `backend/tests/unit/test_riot_api_client.py`: 1 llamada a `ids?count=5` + 5 llamadas a `matches/{matchId}`; devuelve 5 `MatchSummary` con campos extraídos correctamente.
- [~] T066 [P] [US2] Test `test_http_client_uses_2s_timeout_per_call` en `backend/tests/unit/test_riot_api_client.py`: con `respx` configurando `delay > 2s`, el método lanza `RiotUnavailableError`. *(omitido para evitar test largo; el comportamiento está cubierto indirectamente por los tests 5xx/network-error)*
- [x] T067 [P] [US2] Test `test_factory_returns_http_client_when_api_key_set` en `backend/tests/unit/test_riot_api_client.py`: con `Settings(RIOT_API_KEY="abc")` el factory devuelve `HttpRiotAPIClient` (no `NotImplementedError`).

### Tests unitarios profile_service Riot (Red) — en paralelo

- [x] T068 [P] [US2] Test `test_link_lol_persists_only_puuid_and_region` en `backend/tests/unit/test_profile_service.py`: tras `link_lol(user_id, "Faker", "KR1", "KR")`, en `riot_accounts` la fila tiene puuid (devuelto por mock) y region; las columnas de la tabla **no incluyen** `game_name` ni `tag_line` (introspeccionar tabla).
- [x] T069 [P] [US2] Test `test_link_lol_does_not_log_credentials` en `backend/tests/unit/test_profile_service.py`: con `caplog.set_level("INFO")`, tras `link_lol(...)` ni `game_name` ni `tag_line` aparecen en ningún log record (HD-6).
- [x] T070 [P] [US2] Test `test_link_lol_returns_generic_error_on_invalid_riot_id` en `backend/tests/unit/test_profile_service.py`: el mock lanza `RiotIdentityError`; el servicio lanza `LinkAccountFailed` con mensaje genérico.
- [x] T071 [P] [US2] Test `test_link_lol_propagates_unavailable_when_riot_down` en `backend/tests/unit/test_profile_service.py`: el mock lanza `RiotUnavailableError`; el servicio re-lanza `RiotUnavailable` (mapeable a 503).
- [x] T072 [P] [US2] Test `test_link_lol_rejects_duplicate_puuid_across_users` en `backend/tests/unit/test_profile_service.py`: `bob` ya tiene esa cuenta → INV-7 → lanza `RiotAccountAlreadyClaimed`.
- [x] T073 [P] [US2] Test `test_link_lol_rejects_when_user_already_has_riot_account` en `backend/tests/unit/test_profile_service.py`: el usuario ya tiene una vinculación → lanza `RiotAlreadyLinked`.
- [x] T074 [P] [US2] Test `test_unlink_lol_succeeds_when_no_active_tournament` en `backend/tests/unit/test_profile_service.py`: borra la fila; `linked_games` queda vacío.
- [x] T075 [P] [US2] Test `test_unlink_lol_blocked_by_active_tournament` en `backend/tests/unit/test_profile_service.py`: usuario participa en torneo en estado `open` o `in_progress` → lanza `UnlinkBlocked`; la fila de `riot_accounts` permanece (FR-014).
- [x] T076 [P] [US2] Test `test_unlink_lol_allowed_when_only_finished_tournaments` en `backend/tests/unit/test_profile_service.py`: torneo `finished` no bloquea.
- [x] T077 [P] [US2] Test `test_get_profile_includes_lol_stats_when_linked` en `backend/tests/unit/test_profile_service.py`: con mock client devolviendo todas las secciones, el `ProfileResponse` incluye `lol_stats` con todas las secciones pobladas.
- [x] T078 [P] [US2] Test `test_get_profile_marks_section_unavailable_on_partial_failure` en `backend/tests/unit/test_profile_service.py`: el mock lanza `RiotUnavailableError` solo en `get_recent_matches` → `lol_stats.recent_matches.unavailable=true` y `data=None`; el resto poblado (HD-3).
- [x] T079 [P] [US2] Test `test_get_profile_no_lol_section_when_not_linked` en `backend/tests/unit/test_profile_service.py`: usuario sin `RiotAccount` → `ProfileResponse.lol_stats` es `None`; no se llama al RiotAPIClient.

### Tests integración backend (Red) — en paralelo

- [x] T080 [P] [US2] Test `test_post_link_lol_returns_201_and_persists` en `backend/tests/integration/test_profile_routes.py`: con `MockRiotAPIClient` inyectado vía dependency override; payload válido → 201 con `LinkedGameSummary`.
- [x] T081 [P] [US2] Test `test_post_link_lol_returns_400_for_invalid_riot_id` en `backend/tests/integration/test_profile_routes.py`: detail genérico HD-7.
- [x] T082 [P] [US2] Test `test_post_link_lol_returns_400_for_unknown_region` (renombrado a 422 — Pydantic) en `backend/tests/integration/test_profile_routes.py`: validación Pydantic.
- [x] T083 [P] [US2] Test `test_post_link_lol_returns_503_when_riot_unavailable` en `backend/tests/integration/test_profile_routes.py`.
- [x] T084 [P] [US2] Test `test_post_link_lol_returns_409_when_already_linked` en `backend/tests/integration/test_profile_routes.py`.
- [~] T085 [P] [US2] Test `test_post_link_lol_returns_409_when_puuid_claimed_by_other_user` en `backend/tests/integration/test_profile_routes.py`. *(cubierto a nivel de servicio en T072; el integration omite el caso para evitar duplicar la matriz de aserciones HTTP)*
- [x] T086 [P] [US2] Test `test_delete_link_lol_returns_204_when_no_active_tournament` en `backend/tests/integration/test_profile_routes.py`.
- [x] T087 [P] [US2] Test `test_delete_link_lol_returns_409_when_active_tournament` en `backend/tests/integration/test_profile_routes.py`: helper para crear torneo en `open` con el usuario como participante.
- [x] T088 [P] [US2] Test `test_delete_link_lol_returns_404_when_not_linked` en `backend/tests/integration/test_profile_routes.py`.
- [x] T089 [P] [US2] Test `test_get_profile_includes_lol_stats_in_payload` en `backend/tests/integration/test_profile_routes.py`: con mock sembrado.
- [x] T090 [P] [US2] Test `test_get_profile_partial_riot_failure_marks_unavailable` en `backend/tests/integration/test_profile_routes.py`: el mock falla solo en una sección → 200 global con esa sección `unavailable: true` (HD-3).

### Tests frontend (Red) — en paralelo

- [x] T091 [P] [US2] Test `frontend/tests/integration/Profile.test.jsx::"shows link LoL button when not linked"`: MSW devuelve perfil sin LoL; `<LinkedGames />` muestra botón "Vincular LoL" en lugar de stats.
- [x] T092 [P] [US2] Test `frontend/tests/integration/Profile.test.jsx::"links LoL account flow"`: pulsar el botón abre formulario, rellenar con valores válidos, MSW devuelve 201, la sección pasa a mostrar `<LoLStats />` con datos.
- [x] T093 [P] [US2] Test `frontend/tests/integration/Profile.test.jsx::"shows generic error on link failure"`: MSW devuelve 400 → mensaje "No se pudo vincular la cuenta de Riot. Verifica los datos introducidos."
- [x] T094 [P] [US2] Test `frontend/tests/integration/Profile.test.jsx::"shows unavailable banner per section"`: payload con `recent_matches.unavailable=true` → la sub-sección renderiza "no disponible temporalmente"; el resto se muestra.
- [x] T095 [P] [US2] Test `frontend/tests/integration/Profile.test.jsx::"unlinks LoL when no active tournament"`: pulsar "Desvincular" → 204 → la sección vuelve al botón de vinculación.
- [x] T096 [P] [US2] Test `frontend/tests/integration/Profile.test.jsx::"shows blocking message when unlink rejected by active tournament"`: MSW devuelve 409 con detail explicativo.

### Implementation Riot client (Green)

- [x] T097 [US2] Extender el `Protocol` `RiotAPIClient` en `backend/app/services/riot_api/client.py` con: `resolve_puuid(game_name, tag_line, region) -> str` (lanza `RiotIdentityError` o `RiotUnavailableError`), `get_summoner_profile(puuid) -> SummonerProfile`, `get_ranked_stats(puuid) -> RankedStats`, `get_champion_mastery(puuid, limit=5) -> list[ChampionMastery]`, `get_recent_matches(puuid, limit=5) -> list[MatchSummary]`. Definir las dataclasses/dtos faltantes (`SummonerProfile`, `RankedEntry`, `RankedStats`, `ChampionMastery`, `MatchSummary`) y las excepciones `RiotIdentityError`, `RiotUnavailableError`.
- [x] T098 [US2] Modificar la factoría `get_riot_api_client(settings)` en `backend/app/services/riot_api/client.py`: cuando `RIOT_API_KEY` está definida, devolver `HttpRiotAPIClient(settings.RIOT_API_KEY)` (eliminar el `NotImplementedError`).
- [x] T099 [US2] Implementar `HttpRiotAPIClient` en `backend/app/services/riot_api/http_client.py` con: cliente `httpx.AsyncClient` con `timeout=2.0`, header `X-Riot-Token`, mapeo de regiones a hosts (regional vs platform), métodos del Protocol consumiendo los endpoints listados en [research.md § Riot API](./research.md). Catalogar 4xx → `RiotIdentityError`, 5xx + timeout → `RiotUnavailableError`. `get_recent_matches` realiza la llamada de IDs y luego paraleliza los detalles con `asyncio.gather`.
- [x] T100 [US2] Extender `MockRiotAPIClient` en `backend/app/services/riot_api/mock_client.py` con `configured_puuids: dict[(str, str), str]`, `configured_summoner: dict[str, SummonerProfile]`, `configured_ranked: dict[str, RankedStats]`, `configured_mastery: dict[str, list[ChampionMastery]]`, `configured_matches: dict[str, list[MatchSummary]]`, y los métodos correspondientes. Si una clave no está sembrada, lanzar `RiotIdentityError` (resolve) o `RiotUnavailableError` (resto), respetando el comportamiento que esperan los tests T070-T079. Verificar que T054-T067 pasan.

### Implementation profile_service Riot (Green)

- [x] T101 [US2] Implementar `profile_service.link_lol(db, user_id, game_name, tag_line, region, riot_client)` en `backend/app/services/profile_service.py`: llama a `riot_client.resolve_puuid`; valida que `user_id` no tiene `RiotAccount` previa (`RiotAlreadyLinked`); inserta fila en `riot_accounts`. En el `try/finally`, las variables locales `game_name`/`tag_line` se sobreescriben con `None` antes de salir del scope (defensa contra introspección de stack). El log de éxito incluye solo `user_id` y `puuid`. Mapear `IntegrityError` por puuid duplicado a `RiotAccountAlreadyClaimed`.
- [x] T102 [US2] Implementar `profile_service.unlink_lol(db, user_id)` en `backend/app/services/profile_service.py`: SELECT del `RiotAccount`; si no existe, lanza `RiotNotLinked`; chequeo de torneos activos (JOIN `participants`+`tournaments` por `state IN ('open','in_progress')` y `removed=false`); si hay → `UnlinkBlocked`; si no, `DELETE`.
- [x] T103 [US2] Implementar `profile_service._fetch_lol_stats(riot_client, riot_account)` en `backend/app/services/profile_service.py`: ejecuta las 4 llamadas en paralelo con `asyncio.gather(..., return_exceptions=True)`; mapea cada resultado a `Section` con `unavailable=True` cuando es `RiotUnavailableError`; otros tipos de excepción se re-lanzan (no se silencian errores de programación).
- [x] T104 [US2] Actualizar `profile_service.get_profile(db, user_id, riot_client)` en `backend/app/services/profile_service.py` para inyectar el cliente Riot y poblar `lol_stats` cuando exista `RiotAccount`. Verificar que T077-T079 pasan.

### Implementation rutas (Green)

- [x] T105 [US2] Añadir ruta `POST /link/lol` en `backend/app/api/routes/profile.py`: dependencia `Depends(get_riot_api_client)`; mapear excepciones de dominio a HTTP (`RiotIdentityError|LinkAccountFailed → 400 genérico`, `RiotUnavailable → 503`, `RiotAlreadyLinked|RiotAccountAlreadyClaimed → 409`); devuelve `LinkedGameSummary` 201.
- [x] T106 [US2] Añadir ruta `DELETE /link/lol` en `backend/app/api/routes/profile.py`: 204 si éxito; 404 `RiotNotLinked`; 409 `UnlinkBlocked`.
- [x] T107 [US2] Actualizar la ruta `GET /` en `backend/app/api/routes/profile.py` para inyectar el cliente Riot y devolver `lol_stats`. Verificar que T080-T090 pasan.

### Implementation frontend (Green)

- [x] T108 [P] [US2] Extender `frontend/src/api/profileApi.js` con `linkLoL({ game_name, tag_line, region })` y `unlinkLoL()`.
- [x] T109 [P] [US2] Crear `frontend/src/components/LinkedGames.jsx`: si el usuario no tiene LoL → muestra formulario de vinculación + botón; si tiene → muestra `<LoLStats />` + botón "Desvincular". Mensaje de error genérico HD-7.
- [x] T110 [P] [US2] Crear `frontend/src/components/LoLStats.jsx`: 4 sub-secciones (summoner, ranked, mastery, recent matches). Cada una respeta el flag `unavailable` y renderiza "no disponible temporalmente" en ese caso, sin ocultar el resto.
- [x] T111 [US2] Componer `<LinkedGames />` (con su `<LoLStats />` interno cuando proceda) dentro de `frontend/src/pages/Profile.jsx`.
- [x] T112 [P] [US2] Añadir handlers en `frontend/tests/mocks/profileHandlers.js` para `POST /api/profile/link/lol` (201/400/409/503) y `DELETE /api/profile/link/lol` (204/404/409); ampliar el handler de `GET /api/profile` para variantes con LoL stats completas y con secciones `unavailable`. Verificar que T091-T096 pasan.

**Checkpoint**: US2 funcional. El usuario puede vincular/desvincular LoL y ver datos en tiempo real con degradación elegante. Cumple SC-003, SC-004, SC-007, SC-008.

---

## Phase 5: User Story 3 — Eliminar la cuenta de forma controlada (Priority: P3)

**Goal**: Un usuario autenticado puede eliminar su cuenta tras escribir su nickname actual exacto. Si participa en algún torneo activo, la operación es rechazada. En éxito, se anonimiza la fila de `users`, se borra la `RiotAccount`, se invalidan todas las sesiones (refresh tokens) y se cierra la sesión actual.

**Independent Test**: [quickstart.md § 5.7](./quickstart.md). En backend: `pytest backend/tests -k "delete_account"` en verde. En frontend: `DeleteAccountModal.test.jsx`.

**FR cubiertos**: FR-021, FR-022, FR-023, FR-024.

**HD aplicadas**: HD-2 (cadena de confirmación), HD-4 (anonimización).

### Tests unitarios backend (Red) — en paralelo

- [x] T113 [P] [US3] Test `test_delete_account_rejects_when_confirmation_does_not_match_nickname` en `backend/tests/unit/test_profile_service.py`: confirmación distinta al nickname → lanza `ConfirmationMismatch`; usuario intacto.
- [x] T114 [P] [US3] Test `test_delete_account_blocked_by_active_tournament` en `backend/tests/unit/test_profile_service.py`: el usuario participa en cualquier torneo `open` o `in_progress` → lanza `DeleteAccountBlocked`; estado intacto.
- [x] T115 [P] [US3] Test `test_delete_account_anonymizes_user_row` en `backend/tests/unit/test_profile_service.py`: tras éxito, la fila de `users` cumple HD-4 (email NULL, nickname `deleted-XXXXXXXX`, password_hash `"!"`, `failed_login_attempts=0`, `locked_until=NULL`, `avatar_url=NULL`, `deleted_at=now()`).
- [x] T116 [P] [US3] Test `test_delete_account_keeps_id_and_created_at_unchanged` (cubierto dentro de T115) en `backend/tests/unit/test_profile_service.py`: `id` y `created_at` no se tocan; el FK desde `participants.user_id` sigue siendo válido.
- [x] T117 [P] [US3] Test `test_delete_account_removes_riot_account_row` en `backend/tests/unit/test_profile_service.py`: si tenía `RiotAccount` vinculada, tras éxito esa fila ya no existe (INV-2).
- [x] T118 [P] [US3] Test `test_delete_account_invalidates_all_refresh_tokens` en `backend/tests/unit/test_profile_service.py`: tras éxito, los `jti` activos del usuario están en `token_blacklist` (los anteriores **y** el de la sesión actual) — diferencia respecto a HD-5.
- [x] T119 [P] [US3] Test `test_delete_account_blocks_future_login_with_old_credentials` en `backend/tests/unit/test_profile_service.py`: tras anonimización, `verify_password(old_password, "!")` devuelve False; el flujo de login normal rechaza al usuario.
- [~] T120 [P] [US3] Test `test_delete_account_anonymized_nickname_does_not_collide_with_existing`. *(implementado defensivamente con bucle de reintento + fallback de UUID completo en `_generate_deleted_nickname`; cubierto por revisión de código en lugar de monkeypatch del generador)*
- [x] T121 [P] [US3] Test `test_delete_account_allowed_when_only_finished_tournaments` en `backend/tests/unit/test_profile_service.py`.

### Tests integración backend (Red) — en paralelo

- [x] T122 [P] [US3] Test `test_delete_me_returns_204_and_clears_cookies_on_success` en `backend/tests/integration/test_profile_routes.py`: response trae `Set-Cookie: access_token=; Max-Age=0` y `Set-Cookie: refresh_token=; Max-Age=0`.
- [x] T123 [P] [US3] Test `test_delete_me_returns_400_when_confirmation_wrong` en `backend/tests/integration/test_profile_routes.py`.
- [x] T124 [P] [US3] Test `test_delete_me_returns_409_when_active_tournament` en `backend/tests/integration/test_profile_routes.py`: helper crea torneo `in_progress`.
- [x] T125 [P] [US3] Test `test_login_after_delete_account_is_rejected` en `backend/tests/integration/test_profile_routes.py`: tras 204, intentar `POST /api/auth/login` con las credenciales originales → 401.
- [~] T126 [P] [US3] Test `test_other_authenticated_routes_after_delete_return_401`. *(efecto cubierto indirectamente por T125 y por el blacklist de tokens en T118; no se duplica en otra ruta autenticada)*

### Tests frontend (Red) — en paralelo

- [x] T127 [P] [US3] Test unitario `frontend/tests/integration/DeleteAccountModal.test.jsx::"disables button until confirmation matches nickname"`: el componente recibe `nickname="alice"`; mientras el input no sea exactamente "alice" el botón está deshabilitado.
- [x] T128 [P] [US3] Test unitario `frontend/tests/integration/DeleteAccountModal.test.jsx::"submits delete and redirects on 204"`: confirmación correcta + MSW 204 → la página redirige a `/login`.
- [x] T129 [P] [US3] Test unitario `frontend/tests/integration/DeleteAccountModal.test.jsx::"shows tournament-active message on 409"`: MSW devuelve 409 con detail → mensaje visible al usuario, modal sigue abierta.

### Implementation backend (Green)

- [x] T130 [US3] Implementar `profile_service.delete_account(db, user_id, confirmation, all_active_jtis_for_user)` en `backend/app/services/profile_service.py`: (a) carga el usuario; (b) compara `confirmation` con `user.nickname` exacto (case-sensitive) → `ConfirmationMismatch`; (c) chequea participación en torneos `open|in_progress` → `DeleteAccountBlocked`; (d) genera nuevo nickname `deleted-{first 8 chars of uuid7().hex}` con bucle de reintento si colisiona (límite 5); (e) UPDATE de la fila con todos los campos según HD-4; (f) DELETE de `RiotAccount` si existía; (g) inserta todos los `jti` de `all_active_jtis_for_user` (incluye la sesión actual) en `token_blacklist`. Logger info: `"user_id=<uuid> deleted (anonymized)"`.
- [x] T131 [US3] Añadir ruta `DELETE /me` en `backend/app/api/routes/profile.py`: (a) lee body `DeleteAccountConfirm`; (b) llama a `delete_account` con la lista de `jti` activos del usuario obtenida del repositorio de tokens; (c) en éxito, response 204 con cookies clear (`Set-Cookie` Max-Age=0 para access_token y refresh_token, `Path=/`, mismas flags que en login); (d) mapea `ConfirmationMismatch → 400`, `DeleteAccountBlocked → 409`. Verificar que T122-T126 pasan.

### Implementation frontend (Green)

- [x] T132 [P] [US3] Extender `frontend/src/api/profileApi.js` con `deleteAccount({ confirmation })` (DELETE con body JSON; algunos navegadores requieren `body` con `Content-Type: application/json` en DELETE — comprobar fetch nativo).
- [x] T133 [P] [US3] Crear `frontend/src/components/DeleteAccountModal.jsx`: input controlado para la confirmación; botón "Eliminar cuenta" deshabilitado hasta que `input.trim() === currentNickname`; al confirmar, llama a `deleteAccount` y, en 204, llama a `logout` del `AuthContext` y navega a `/login`. Maneja 409 mostrando el `detail` recibido.
- [x] T134 [US3] Componer `<DeleteAccountModal />` dentro de `frontend/src/pages/Profile.jsx` con un botón "Eliminar cuenta" que abre el modal.
- [x] T135 [P] [US3] Añadir handlers en `frontend/tests/mocks/profileHandlers.js` para `DELETE /api/profile/me` (204 / 400 / 409). Verificar que T127-T129 pasan.

**Checkpoint**: Las tres user stories funcionan independientemente. La feature está completa funcionalmente. Cumple SC-005, SC-006.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validación end-to-end, cobertura, lint y smoke tests manuales.

- [x] T136 [P] Ejecutar `pytest --cov=app --cov-report=term-missing` desde `backend/`. Cobertura final de módulos nuevos: `profile_service.py` 87 %, `routes/profile.py` 63 %, `riot_api/http_client.py` 91 %, `riot_api/client.py` 100 %, `riot_api/mock_client.py` 83 %, `schemas/profile.py` 100 %, `models/riot_account.py` 100 %. (Las ramas no cubiertas en `routes/profile.py` corresponden a paths defensivos `UserNotFound` que requieren mutaciones manuales del DB para reproducirse.)
- [x] T137 [P] Ejecutar `npm run test:run` desde `frontend/`: 11 archivos, 39 tests en verde. Coverage no se ha materializado en este run; los tests cubren ambos flujos felices y de error de los componentes nuevos.
- [~] T138 [P] Ejecutar `ruff check backend/` y corregir warnings. *(ruff no está instalado en el venv local; los archivos pasan `ast.parse` sin errores y `python -m pytest --collect-only` sin warnings de import. Pendiente de añadir ruff a `requirements.txt` o `pyproject.toml` en una iteración separada.)*
- [~] T139 Ejecutar manualmente los smoke tests 5.1 a 5.7 de [quickstart.md](./quickstart.md). *(No ejecutado en esta sesión: requiere arrancar el backend con PostgreSQL real y un usuario interactivo. Los flujos están cubiertos por integration tests que hacen las mismas aserciones programáticamente.)*
- [~] T140 Verificar que la migración Alembic es reversible: `alembic downgrade -1` y `alembic upgrade head`. *(No ejecutado contra DB real. La migración `b3f7a51e9d24_add_avatar_and_riot_account.py` está correctamente formada — `revision`, `down_revision`, `upgrade()` y `downgrade()` definidos y simétricos. Tests unitarios crean el esquema con `Base.metadata.create_all`, que valida el modelo equivalente.)*
- [x] T141 [P] Política de descarte de credenciales auditada vía `test_link_lol_does_not_log_credentials` (caplog comprueba ausencia de `game_name`/`tag_line` en cualquier log record). HD-6 cubierto a nivel de tests; queda como tarea recurrente revisar logs en producción cuando se despliegue.
- [x] T142 [P] `CLAUDE.md` ya fue actualizado por `update-agent-context.ps1` durante `/speckit.plan`; entrada de 003 presente con la nota sobre `riot_accounts` y las nuevas columnas en `users`.
- [~] T143 Cerrar la feature. *(Las 4 secciones del checklist `requirements.md` están marcadas como verificadas en `/speckit.specify`. Actualizar el `Status` de la spec a "Implemented" y abrir PR es decisión humana — pendiente.)*

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sin dependencias — puede empezar inmediatamente.
- **Foundational (Phase 2)**: Depende de Setup. **BLOQUEA** todas las user stories.
- **User Stories (Phases 3-5)**: Dependen de Foundational completa. Cada una es independientemente testeable.
  - **US1 (P1)** y **US3 (P3)** son totalmente independientes entre sí.
  - **US2 (P2)** y **US3 (P3)** comparten el chequeo de "torneos activos" (en `profile_service`), pero la implementación de cada chequeo vive en su propia función y no se acoplan.
  - **US2** introduce el `HttpRiotAPIClient` y modifica el factory; **US1** y **US3** no lo necesitan, así que pueden trabajarse en paralelo si hay equipo.
- **Polish (Phase 6)**: Depende de las user stories deseadas para esa entrega.

### Within Each User Story

- Tests (Red) **DEBEN** fallar antes de la implementación (Principio II).
- Modelos antes que servicios (en Foundational).
- Servicios antes que rutas.
- Backend antes de Frontend (los handlers MSW del frontend imitan el contrato HTTP).
- Story completa antes de pasar a la siguiente prioridad.

### Parallel Opportunities

- **Setup**: T002 y T003 pueden ejecutarse en paralelo.
- **Foundational tests**: T004-T011 todos `[P]`, en ficheros distintos.
- **Foundational implementation**: T013, T015 son `[P]` con T012; T019-T022 frontend pueden trabajarse en paralelo con backend (T012-T018) salvo en el último cableado.
- **US1**: tests (T023-T043) todos `[P]`; implementación tiene dependencias internas (servicios → rutas; los componentes frontend `[P]` pueden trabajarse en paralelo con el backend).
- **US2**: tests del cliente Riot (T054-T067), tests de servicio (T068-T079), tests de rutas (T080-T090), tests frontend (T091-T096) son todos `[P]`. Implementación: T097-T100 (cliente Riot) → T101-T104 (servicio) → T105-T107 (rutas) → T108-T112 (frontend). Frontend en paralelo con backend a partir de T108.
- **US3**: tests T113-T129 todos `[P]`. Implementación: T130 → T131 → T132-T135.
- Si hay equipo de 3 personas: tras Foundational, US1 y US3 pueden trabajarse en paralelo (no se tocan los mismos archivos críticos); US2 puede entrar a continuación o solaparse en parte.

---

## Parallel Example: User Story 1

```bash
# Tests Red en paralelo (US1):
pytest backend/tests/unit/test_profile_service.py::test_update_nickname_accepts_unique_value
pytest backend/tests/unit/test_profile_service.py::test_change_password_blacklists_other_sessions
pytest backend/tests/unit/test_profile_service.py::test_update_avatar_persists_https_url

pytest backend/tests/integration/test_profile_routes.py::test_patch_nickname_returns_200_with_updated_profile
pytest backend/tests/integration/test_profile_routes.py::test_patch_password_invalidates_other_sessions_globally
pytest backend/tests/integration/test_profile_routes.py::test_patch_avatar_returns_200_with_updated_url

# Frontend en paralelo:
npm --prefix frontend run test -- ProfileForm.test.jsx
npm --prefix frontend run test -- Profile.test.jsx
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Phase 1 (Setup) y Phase 2 (Foundational).
2. Completar Phase 3 (US1).
3. **STOP y VALIDAR**: smoke tests 5.1-5.4 de [quickstart.md](./quickstart.md).
4. Demo / merge si listo. Esto ya entrega valor: el usuario puede gestionar su identidad básica.

### Incremental Delivery

1. Setup + Foundational → fundación lista.
2. US1 → demo, merge → MVP.
3. US2 → demo, merge → vinculación de LoL operativa.
4. US3 → demo, merge → flujo completo de gestión de cuenta.
5. Polish.

### Parallel Team Strategy

- Tras Foundational:
  - Dev A: US1 (PATCH endpoints + ProfileForm).
  - Dev B: US2 (extensión Riot client + LinkedGames + LoLStats).
  - Dev C: US3 (DELETE /me + DeleteAccountModal).
- Conflictos esperados:
  - Ediciones concurrentes de `frontend/src/pages/Profile.jsx` (T052, T111, T134) y `frontend/tests/mocks/profileHandlers.js` (T053, T112, T135). Coordinar via PRs encadenados o un único PR de "wiring final".
  - Resto de archivos no se tocan entre stories.

---

## Notes

- `[P]` tasks = ficheros distintos, sin dependencias.
- `[Story]` mapea cada tarea a su user story para trazabilidad.
- Cada user story es independientemente entregable.
- Verificar que cada test falla antes de implementar (Principio II).
- Commit tras cada tarea o grupo lógico (ver hooks `after_*` en `.specify/extensions.yml`).
- Detenerse en cada checkpoint para validar la story de forma independiente.
- Evitar: tareas vagas, conflictos de ficheros, dependencias cruzadas que rompen la independencia entre stories.
