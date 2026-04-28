---
description: "Task list for feature 004-add-friends: Añadir amigos"
---

# Tasks: Añadir amigos

**Input**: Design documents from `specs/004-add-friends/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: TDD es **OBLIGATORIO** por la Constitución (Principio II, NO NEGOCIABLE). Cada tarea de test debe fallar (Red) antes de escribir la implementación asociada (Green).

**Organization**: Tareas agrupadas por user story en su orden de prioridad. La numeración `US1, US2` se preserva tal cual aparece en [spec.md](./spec.md).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo con otras `[P]` del mismo bloque (ficheros distintos, sin dependencias pendientes).
- **[Story]**: `US1`, `US2` para tareas de historia. Setup, Foundational y Polish no llevan etiqueta de historia.
- Todos los paths son relativos a la raíz del repositorio.

## Path Conventions

Estructura fijada en [plan.md § Project Structure](./plan.md) (Variante B — backend API + frontend SPA):

- Backend: `backend/app/**`, `backend/tests/**`
- Frontend: `frontend/src/**`, `frontend/tests/**`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Esta iteración **no introduce dependencias**. Setup se reduce a verificar el entorno y preparar los huecos donde los ficheros nuevos van a aparecer.

- [ ] T001 Verificar que `backend/requirements.txt` y `frontend/package.json` no requieren altas para 004 (research.md § CVE Audit). Si en el camino aparece la necesidad de una dependencia, levantar audit explícito antes de instalar (Constitución I).
- [ ] T002 [P] Verificar/crear (con `.gitkeep` si vacíos) los subdirectorios usados por la feature: `backend/app/api/routes/` (existe), `backend/app/models/` (existe), `backend/app/schemas/` (existe), `backend/app/services/` (existe), `frontend/src/components/` (existe), `frontend/src/pages/` (existe), `frontend/tests/mocks/` (existe). No se crean carpetas nuevas; tarea de chequeo.
- [ ] T003 [P] Confirmar que `.specify/feature.json` apunta a `specs/004-add-friends` (lo dejó así `/speckit.specify`). Cualquier desviación debe corregirse antes de continuar.

**Checkpoint**: Setup listo. Todas las dependencias necesarias ya están instaladas desde 001/002/003.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestructura transversal que **toda** user story consume: modelo `Friendship`, migración Alembic con el ENUM `friendship_status`, esquemas Pydantic v2 (incluido `FriendshipStatus`), router base de `/api/friends`, registro en `main.py`, fixtures de tests para parejas de usuarios y para relaciones pre-existentes (pending/accepted), y la función `friends_service.compute_relationship_status` (la única lógica de servicio compartida por las dos stories).

**⚠️ CRITICAL**: Ninguna user story puede empezar hasta que esta fase esté completa.

### Tests (Red — deben fallar antes de implementar)

- [ ] T004 [P] Test unitario `backend/tests/unit/test_models.py::test_friendship_unique_per_direction`: insertar dos `Friendship` con el mismo `(requester_id, addressee_id)` falla por `UNIQUE`; insertar `(A,B)` y `(B,A)` está permitido a nivel BD (la lógica de servicio lo bloqueará con HD-3 en US2). INV-1 de [data-model.md](./data-model.md).
- [ ] T005 [P] Test unitario `backend/tests/unit/test_models.py::test_friendship_check_no_self_link`: insertar `Friendship(requester_id=X, addressee_id=X)` falla por `CHECK (requester_id <> addressee_id)`. INV-2 de [data-model.md](./data-model.md).
- [ ] T006 [P] Test unitario `backend/tests/unit/test_models.py::test_friendship_status_enum_values`: el enum `friendship_status` acepta `'pending'` y `'accepted'`; cualquier otro valor falla a nivel BD/SQLAlchemy.
- [ ] T007 [P] Test unitario `backend/tests/unit/test_friends_schemas.py::test_friendship_status_enum_serialization` en `backend/tests/unit/test_friends_schemas.py`: el enum Pydantic `FriendshipStatus` serializa exactamente como `SIN_RELACION`, `PENDIENTE_ENVIADA`, `PENDIENTE_RECIBIDA`, `AMIGO`. Cualquier otro valor lanza `ValidationError`.
- [ ] T008 [P] Test unitario `backend/tests/unit/test_friends_schemas.py::test_user_search_result_includes_relationship_status`: `UserSearchResult` requiere `id`, `nickname`, `avatar_url` (nullable) y `relationship_status` (enum). Falta de cualquiera lanza `ValidationError`.
- [ ] T009 [P] Test unitario `backend/tests/unit/test_friends_schemas.py::test_friend_request_response_shape`: `FriendRequestResponse` requiere `id`, `requester_id`, `addressee_id`, `requester_nickname`, `requester_avatar_url` (nullable), `created_at`.
- [ ] T010 [P] Test unitario `backend/tests/unit/test_friends_schemas.py::test_friend_request_action_result_enum_action`: `FriendRequestActionResult.action` acepta solo `"accepted"` y `"rejected"`.
- [ ] T011 [P] Test unitario `backend/tests/unit/test_friends_service.py::test_compute_relationship_status_when_no_relation` en `backend/tests/unit/test_friends_service.py`: con BD vacía de `friendships`, `compute_relationship_status(db, alice.id, bob.id)` → `SIN_RELACION`. INV-3 de [data-model.md](./data-model.md).
- [ ] T012 [P] Test unitario `backend/tests/unit/test_friends_service.py::test_compute_relationship_status_when_pending_sent`: insertando `Friendship(requester=alice, addressee=bob, status='pending')`, `compute_relationship_status(db, alice.id, bob.id)` → `PENDIENTE_ENVIADA` y `compute_relationship_status(db, bob.id, alice.id)` → `PENDIENTE_RECIBIDA`. INV-3 (HD-1).
- [ ] T013 [P] Test unitario `backend/tests/unit/test_friends_service.py::test_compute_relationship_status_when_accepted`: con `Friendship(..., status='accepted')`, ambos sentidos → `AMIGO`. INV-3.
- [ ] T014 [P] Test integración `backend/tests/integration/test_friends_routes.py::test_friends_search_requires_authentication`: `GET /api/friends/search?q=foo` sin cookie → 401. Crear el archivo si no existe.
- [ ] T015 [P] Test integración `backend/tests/integration/test_friends_routes.py::test_friends_requests_endpoint_requires_authentication`: `GET /api/friends/requests` sin cookie → 401.

### Implementation (Green)

- [ ] T016 Crear `Friendship` model en `backend/app/models/friendship.py` con: `id (UUID PK)`, `requester_id (UUID FK users.id ON DELETE CASCADE, NOT NULL)`, `addressee_id (UUID FK users.id ON DELETE CASCADE, NOT NULL)`, `status (Enum 'pending'|'accepted', NOT NULL)`, `created_at (TIMESTAMPTZ default now)`. Constraints: `UniqueConstraint('requester_id', 'addressee_id')`, `CheckConstraint('requester_id <> addressee_id')`. Índices: `idx_friendships_requester (requester_id, status)`, `idx_friendships_addressee (addressee_id, status)`. Registrar el import en `backend/app/db/base.py` para que Alembic lo detecte.
- [ ] T017 Generar migración Alembic `backend/app/db/migrations/versions/<hash>_add_friendships.py` que (a) cree el tipo enum PostgreSQL `friendship_status AS ENUM ('pending', 'accepted')`, (b) cree la tabla `friendships` con sus columnas, índices y constraints. `downgrade()` revierte ambos pasos en orden inverso (`DROP TABLE friendships`, `DROP TYPE friendship_status`). Aplicar `alembic upgrade head` y verificar que T004-T006 pasan.
- [ ] T018 [P] Crear `backend/app/schemas/friends.py` con: `FriendshipStatus(str, Enum)` con valores `SIN_RELACION`, `PENDIENTE_ENVIADA`, `PENDIENTE_RECIBIDA`, `AMIGO`; `UserSearchResult(id: UUID, nickname: str, avatar_url: HttpUrl | None, relationship_status: FriendshipStatus)`; `FriendRequestResponse(id: UUID, requester_id: UUID, addressee_id: UUID, requester_nickname: str, requester_avatar_url: HttpUrl | None, created_at: datetime)`; `FriendRequestActionResult(request_id: UUID, action: Literal["accepted", "rejected"], relationship_status: FriendshipStatus)`. Verificar que T007-T010 pasan.
- [ ] T019 [P] Extender `backend/app/schemas/profile.py` con `PublicProfileResponse` que reutiliza la composición de `ProfileResponse` (heredada de 003) **sin** el campo `email` y **añadiendo** `relationship_status: FriendshipStatus`. Mantener los sub-modelos LoL existentes.
- [ ] T020 Crear `backend/app/services/friends_service.py` con la única función `async def compute_relationship_status(db, current_user_id: UUID, target_user_id: UUID) -> FriendshipStatus` siguiendo la query de [data-model.md § Cálculo del relationship_status](./data-model.md): un único SELECT con `OR` en ambas direcciones, `LIMIT 1`; mapeo del resultado al enum según las cuatro reglas. Verificar que T011-T013 pasan.
- [ ] T021 Crear `backend/app/api/routes/friends.py` con `router = APIRouter(prefix="/friends", tags=["friends"])`. En esta tarea solo se cablea el router vacío; los endpoints concretos se añaden en US1/US2.
- [ ] T022 Registrar el router en `backend/app/main.py`: `app.include_router(friends_router, prefix="/api")`. Añadir un endpoint `GET /search` y un `GET /requests` provisionales que respondan `501 Not Implemented` o que estén ausentes pero el `prefix` registrado, para que T014 y T015 puedan verificar el `401` (FastAPI delega el `401` al middleware de autenticación si la dependencia `get_current_user` se aplica al router; alternativamente, dejar los endpoints sin implementar y comprobar el `401`/`405` esperado en cada caso). Verificar que T014-T015 pasan al cablear la dependencia de autenticación a nivel de router.
- [ ] T023 [P] Extender `backend/tests/conftest.py` con fixtures: `another_user` (usuario distinto al `authenticated_user`), `pending_request_a_to_b` (solicitud `pending` con `requester=alice`, `addressee=bob`), `accepted_friendship_a_b` (fila `accepted` entre `alice` y `bob`), `anonymized_user` (usuario con `deleted_at` no nulo y nickname `deleted-XXXXXXXX`). Reutilizar el patrón de creación de usuarios de 001/002/003.

**Checkpoint**: Foundational lista. La tabla `friendships` existe, los esquemas están definidos, el router de `/api/friends` está montado y `compute_relationship_status` funciona aislado. Las stories ya pueden empezar.

---

## Phase 3: User Story 1 — Buscar usuarios y visualizar su perfil (Priority: P1) 🎯 MVP

**Goal**: Un usuario autenticado introduce texto en un buscador y obtiene una lista de hasta 20 usuarios cuyo nickname contiene la subcadena (ILIKE %q%, case-insensitive), excluyéndose a sí mismo y a usuarios anonimizados. Al pulsar un resultado, navega al perfil del otro usuario, donde ve la misma información que en el suyo (nickname, avatar, juegos vinculados con datos LoL en tiempo real heredados de 003) **sin** opciones de edición y con un campo `relationship_status` calculado.

**Independent Test**: [quickstart.md § 5.1-5.2](./quickstart.md). En backend: `pytest backend/tests -k "search or get_public_profile"` en verde. En frontend: `UserSearchBar.test.jsx` y `UserProfile.test.jsx`.

**FR cubiertos**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, FR-019.

**HD aplicadas**: HD-1 (estado calculado), HD-5 (filtro de anonimizados), HD-6 (mínimo de búsqueda).

### Tests unitarios backend (Red) — en paralelo

- [ ] T024 [P] [US1] Test `test_search_returns_empty_list_for_blank_query` en `backend/tests/unit/test_friends_service.py`: `search_users(db, current_user, q="")` → `[]`; `q="   "` → `[]`. INV-9 / HD-6.
- [ ] T025 [P] [US1] Test `test_search_is_case_insensitive` en `backend/tests/unit/test_friends_service.py`: con usuarios `Alice`, `bob`, `BOBBY`, `search_users(db, current_user=carl, q="BOB")` y `q="bob"` devuelven el mismo conjunto.
- [ ] T026 [P] [US1] Test `test_search_partial_match_inside_nickname` en `backend/tests/unit/test_friends_service.py`: con usuarios `xbobx`, `bobby`, `john`, `q="bob"` devuelve `xbobx` y `bobby` (no solo prefijo).
- [ ] T027 [P] [US1] Test `test_search_limited_to_20_results` en `backend/tests/unit/test_friends_service.py`: insertar 25 usuarios cuyo nickname contiene `"user"`, `q="user"` devuelve exactamente 20.
- [ ] T028 [P] [US1] Test `test_search_excludes_self` en `backend/tests/unit/test_friends_service.py`: con `current_user=alice` cuyo nickname contiene `"al"`, `q="al"` no incluye a alice. INV-9.
- [ ] T029 [P] [US1] Test `test_search_excludes_anonymized_users` en `backend/tests/unit/test_friends_service.py`: con un usuario `deleted-AAAAAAAA` con `deleted_at=now()`, `q="deleted"` no devuelve esa fila. HD-5.
- [ ] T030 [P] [US1] Test `test_search_results_include_relationship_status_per_row` en `backend/tests/unit/test_friends_service.py`: con tres usuarios objetivo (uno sin relación, uno con `pending` enviado por current_user, uno amigo), la lista devuelve `relationship_status` correcto en cada fila sin disparar N+1 (verificar con un spy de `db.execute` que se hacen N+1 queries cuanto mucho — concretamente 1 SELECT de usuarios + 1 SELECT cruzado de friendships).
- [ ] T031 [P] [US1] Test `test_get_public_profile_returns_data_for_existing_user` en `backend/tests/unit/test_profile_service.py`: `get_public_profile(db, nickname="bob", current_user=alice, riot_client=mock)` devuelve `PublicProfileResponse` con `id`, `nickname`, `avatar_url`, `linked_games`, `lol_stats` (si bob tiene RiotAccount) y `relationship_status` calculado vs alice.
- [ ] T032 [P] [US1] Test `test_get_public_profile_does_not_include_email` en `backend/tests/unit/test_profile_service.py`: el dataclass devuelto no contiene un atributo `email` (introspeccionar `model_fields`). HD-7 / FR-008.
- [ ] T033 [P] [US1] Test `test_get_public_profile_raises_not_found_for_unknown_nickname` en `backend/tests/unit/test_profile_service.py`: nickname inexistente → lanza `UserNotFound`.
- [ ] T034 [P] [US1] Test `test_get_public_profile_raises_not_found_for_anonymized_user` en `backend/tests/unit/test_profile_service.py`: nickname pertenece a un usuario con `deleted_at` no nulo → lanza `UserNotFound`. HD-5.

### Tests integración backend (Red) — en paralelo

- [ ] T035 [P] [US1] Test `test_friends_search_returns_results_with_relationship_status` en `backend/tests/integration/test_friends_routes.py`: con `alice` autenticada y `bob` con nickname coincidente, `GET /api/friends/search?q=bob` → 200, lista con un elemento `{ id, nickname: "bob", avatar_url, relationship_status: "SIN_RELACION" }`.
- [ ] T036 [P] [US1] Test `test_friends_search_excludes_authenticated_user` en `backend/tests/integration/test_friends_routes.py`: alice cuyo nickname contiene la subcadena no se autoincluye. FR-002.
- [ ] T037 [P] [US1] Test `test_friends_search_returns_empty_list_when_q_blank` en `backend/tests/integration/test_friends_routes.py`: `GET /api/friends/search?q=` → 200 con `[]`. HD-6.
- [ ] T038 [P] [US1] Test `test_friends_search_q_too_long_returns_422` en `backend/tests/integration/test_friends_routes.py`: `q` con 65 caracteres → 422 (Pydantic). FR-002.
- [ ] T039 [P] [US1] Test `test_friends_search_truncates_to_20_results` en `backend/tests/integration/test_friends_routes.py`: poblar 25 coincidencias → response tiene `len == 20`. INV-11.
- [ ] T040 [P] [US1] Test `test_friends_search_relationship_status_reflects_pending_sent` en `backend/tests/integration/test_friends_routes.py`: con `pending_request_a_to_b`, alice busca `bob` → `relationship_status: "PENDIENTE_ENVIADA"`.
- [ ] T041 [P] [US1] Test `test_friends_search_relationship_status_reflects_accepted` en `backend/tests/integration/test_friends_routes.py`: con `accepted_friendship_a_b`, alice busca `bob` → `relationship_status: "AMIGO"`.
- [ ] T042 [P] [US1] Test `test_get_public_profile_returns_200_for_existing_user` en `backend/tests/integration/test_profile_routes.py`: `GET /api/profile/bob` con sesión válida → 200 con `PublicProfileResponse` (sin `email`, con `relationship_status`).
- [ ] T043 [P] [US1] Test `test_get_public_profile_returns_404_for_unknown_user` en `backend/tests/integration/test_profile_routes.py`: nickname inexistente → 404.
- [ ] T044 [P] [US1] Test `test_get_public_profile_returns_404_for_anonymized_user` en `backend/tests/integration/test_profile_routes.py`: nickname `deleted-XXXXXXXX` → 404. HD-5.
- [ ] T045 [P] [US1] Test `test_get_public_profile_requires_authentication` en `backend/tests/integration/test_profile_routes.py`: sin cookie → 401.
- [ ] T046 [P] [US1] Test `test_get_public_profile_includes_lol_stats_when_target_linked` en `backend/tests/integration/test_profile_routes.py`: con bob vinculado a LoL y `MockRiotAPIClient` sembrado, la respuesta incluye `lol_stats` con secciones pobladas. (Reutiliza el patrón de mock injection de 003.)

### Tests frontend (Red) — en paralelo

- [ ] T047 [P] [US1] Test integración `frontend/tests/integration/UserSearchBar.test.jsx::"shows empty state when input is blank"`: render del componente; sin escribir, no hay dropdown ni llamadas a la API.
- [ ] T048 [P] [US1] Test integración `frontend/tests/integration/UserSearchBar.test.jsx::"debounces input and calls /api/friends/search"`: escribir `bob` → tras el debounce (300 ms simulado con `vi.useFakeTimers`), se hace una sola llamada a `/api/friends/search?q=bob`.
- [ ] T049 [P] [US1] Test integración `frontend/tests/integration/UserSearchBar.test.jsx::"renders results dropdown and navigates on click"`: MSW devuelve dos resultados; el componente los renderiza; click en uno → navega a `/users/{nickname}`.
- [ ] T050 [P] [US1] Test integración `frontend/tests/integration/UserSearchBar.test.jsx::"shows empty state when api returns []"`: MSW devuelve `[]` → mensaje "No hay resultados".
- [ ] T051 [P] [US1] Test integración `frontend/tests/integration/UserProfile.test.jsx::"renders public profile without edit controls"`: ruta `/users/bob`; MSW devuelve `PublicProfileResponse` con `relationship_status: "SIN_RELACION"`; el componente muestra nickname, avatar, juegos vinculados; **NO** muestra inputs de edición de nickname/contraseña/avatar ni botón "Eliminar cuenta".
- [ ] T052 [P] [US1] Test integración `frontend/tests/integration/UserProfile.test.jsx::"renders 404 page when user not found"`: MSW devuelve 404 → mensaje "Usuario no encontrado".
- [ ] T053 [P] [US1] Test integración `frontend/tests/integration/UserProfile.test.jsx::"shows lol stats when target has linked account"`: MSW devuelve `lol_stats` poblado → `<LoLStats />` heredado de 003 se renderiza con los datos.

### Implementation backend (Green)

- [ ] T054 [US1] Implementar `friends_service.search_users(db, current_user_id: UUID, q: str) -> list[UserSearchResult]` en `backend/app/services/friends_service.py`: (a) `q_clean = q.strip()`; si vacío → `[]`; (b) SELECT `users` con `WHERE LOWER(nickname) LIKE LOWER(:pattern) AND id != :current_user_id AND deleted_at IS NULL LIMIT 20`, donde `pattern = f"%{q_clean}%"`; (c) un único SELECT cruzado a `friendships` con los `user_ids` resultantes para calcular `relationship_status` por fila (evitar N+1); (d) construir y devolver `list[UserSearchResult]`. Verificar que T024-T030 pasan.
- [ ] T055 [US1] Implementar `profile_service.get_public_profile(db, nickname: str, current_user_id: UUID, riot_client) -> PublicProfileResponse` en `backend/app/services/profile_service.py`: (a) SELECT user por `nickname` y `deleted_at IS NULL`; si no encuentra → `UserNotFound`; (b) reutilizar la composición ya existente de `get_profile` para `linked_games` y `lol_stats` (pasando el `riot_client` heredado de 003); (c) calcular `relationship_status` con `friends_service.compute_relationship_status(db, current_user_id, target.id)`; (d) construir y devolver `PublicProfileResponse` (sin `email`). Verificar que T031-T034 pasan.
- [ ] T056 [US1] Añadir ruta `GET /search` en `backend/app/api/routes/friends.py`: `Depends(get_current_user)` + `Depends(get_db)`; query param `q: str = Query(default="", max_length=64)`; llama a `friends_service.search_users`; devuelve `list[UserSearchResult]`. Verificar que T035-T041 pasan.
- [ ] T057 [US1] Añadir ruta `GET /{nickname}` en `backend/app/api/routes/profile.py` (debajo de la ruta `GET /` propia): `Depends(get_current_user)` + `Depends(get_db)` + `Depends(get_riot_api_client)`; llama a `profile_service.get_public_profile`; mapea `UserNotFound → 404`; devuelve `PublicProfileResponse`. Verificar que T042-T046 pasan.

### Implementation frontend (Green)

- [ ] T058 [P] [US1] Crear `frontend/src/api/friendsApi.js` con la función `searchUsers(q)` que hace `fetch("/api/friends/search?q=" + encodeURIComponent(q), { credentials: "include" })`. Sin manejo específico de errores.
- [ ] T059 [P] [US1] Extender `frontend/src/api/profileApi.js` con `getPublicProfile(nickname)` que hace `fetch("/api/profile/" + encodeURIComponent(nickname), { credentials: "include" })`.
- [ ] T060 [P] [US1] Crear `frontend/src/components/UserSearchBar.jsx`: input controlado; debounce de 300 ms (puede usar `useEffect` + `setTimeout`/`clearTimeout` o un hook propio inline — sin dependencia externa); al cambiar el input invoca `searchUsers`; renderiza un dropdown con los resultados (lista `UserSearchResult` por fila); cada fila navega a `/users/{nickname}` al pulsar; estado "no resultados" cuando la respuesta es `[]`.
- [ ] T061 [P] [US1] Crear `frontend/src/components/UserSearchResult.jsx`: presentacional; recibe `{ id, nickname, avatar_url, relationship_status }` por props; renderiza avatar + nickname; en US1 **no** monta aún el `FriendshipButton` (eso entra en US2 — el componente queda preparado con un slot para extender).
- [ ] T062 [P] [US1] Crear `frontend/src/pages/UserProfile.jsx`: lee `nickname` desde el path (`useParams`); invoca `getPublicProfile` al montar; estados de loading / error (404) / éxito; renderiza la cabecera con avatar y nickname; renderiza `<LoLStats />` (heredado de 003) si `lol_stats` está presente; **no** muestra `<ProfileForm />`, `<DeleteAccountModal />` ni el bloque de edición de avatar; deja un slot para `<FriendshipButton />` que se monta en US2.
- [ ] T063 [US1] Añadir ruta `/users/:nickname` protegida en `frontend/src/main.jsx` envuelta en `<ProtectedRoute>` que renderiza `<UserProfile />`. Montar `<UserSearchBar />` en el header global (decisión visual — alternativa: componente flotante en `Dashboard.jsx`).
- [ ] T064 [P] [US1] Crear `frontend/tests/mocks/friendsHandlers.js` con un handler para `GET /api/friends/search` que parsea `q` y devuelve un set de mocks coherentes (subset filtrado de un fixture). Registrarlo en `frontend/tests/mocks/server.js` (importar y añadir al array de handlers).
- [ ] T065 [P] [US1] Extender `frontend/tests/mocks/profileHandlers.js` con un handler para `GET /api/profile/:nickname` (200 con `PublicProfileResponse`, 404 para nicknames concretos). Verificar que T047-T053 pasan.

**Checkpoint**: US1 funcional y testeable de forma independiente. El usuario puede buscar a otros usuarios y ver sus perfiles. Cumple SC-001, SC-002, SC-003.

---

## Phase 4: User Story 2 — Enviar y gestionar solicitudes de amistad (Priority: P2)

**Goal**: Desde un resultado de búsqueda o desde el perfil ajeno, el usuario autenticado ve un único botón cuyo estado refleja la relación: "Añadir amigo" si no hay relación, "Pendiente" (disabled) si ya envió solicitud, "Eliminar amigo" si ya son amigos. El destinatario puede aceptar o rechazar las solicitudes recibidas (vía API; la UI del panel principal queda fuera de alcance). El sistema bloquea solicitudes a uno mismo, duplicadas o cruzadas, y la eliminación de amistad es bidireccional.

**Independent Test**: [quickstart.md § 5.3-5.8](./quickstart.md). En backend: `pytest backend/tests -k "send_request or accept_request or reject_request or remove_friend or list_received"` en verde. En frontend: `FriendshipButton.test.jsx` y `UserProfile.test.jsx`.

**FR cubiertos**: FR-009, FR-010, FR-011, FR-012, FR-013, FR-014, FR-015, FR-016, FR-017, FR-018, FR-020, FR-021.

**HD aplicadas**: HD-2 (una fila por relación), HD-3 (race A↔B con SELECT FOR UPDATE), HD-4 (eliminación bidireccional), HD-5 (anonimizados → 404), HD-7 (códigos HTTP).

### Tests unitarios backend (Red) — en paralelo

- [ ] T066 [P] [US2] Test `test_send_request_creates_pending_row` en `backend/tests/unit/test_friends_service.py`: tras `send_request(db, requester=alice, addressee=bob)`, hay una fila `Friendship(requester=alice, addressee=bob, status='pending')`.
- [ ] T067 [P] [US2] Test `test_send_request_to_self_raises_self_friend_request` en `backend/tests/unit/test_friends_service.py`: `send_request(db, requester=alice, addressee=alice)` → lanza `SelfFriendRequest`. INV-5 / FR-014.
- [ ] T068 [P] [US2] Test `test_send_request_rejected_when_already_friends` en `backend/tests/unit/test_friends_service.py`: con `accepted_friendship_a_b`, `send_request(db, requester=alice, addressee=bob)` → lanza `FriendshipAlreadyExists` con `kind="accepted"`. HD-3.
- [ ] T069 [P] [US2] Test `test_send_request_rejected_when_pending_in_same_direction` en `backend/tests/unit/test_friends_service.py`: con `pending_request_a_to_b`, `send_request(db, requester=alice, addressee=bob)` → lanza `FriendshipAlreadyExists` con `kind="pending_sent"`. HD-3.
- [ ] T070 [P] [US2] Test `test_send_request_rejected_when_pending_in_other_direction` en `backend/tests/unit/test_friends_service.py`: con `pending_request_a_to_b`, `send_request(db, requester=bob, addressee=alice)` → lanza `FriendshipAlreadyExists` con `kind="pending_received"`. HD-3 (la rama crítica del flujo cruzado).
- [ ] T071 [P] [US2] Test `test_send_request_to_anonymized_user_raises_not_found` en `backend/tests/unit/test_friends_service.py`: addressee con `deleted_at` no nulo → lanza `UserNotFound`. HD-5.
- [ ] T072 [P] [US2] Test `test_accept_request_updates_status_to_accepted` en `backend/tests/unit/test_friends_service.py`: con `pending_request_a_to_b`, `accept_request(db, request_id, current_user=bob)` → la fila pasa a `status='accepted'` y devuelve `FriendRequestActionResult(action="accepted", relationship_status=AMIGO)`. INV-6.
- [ ] T073 [P] [US2] Test `test_accept_request_forbidden_for_non_addressee` en `backend/tests/unit/test_friends_service.py`: con `pending_request_a_to_b`, `accept_request(db, request_id, current_user=alice)` → lanza `NotRequestAddressee` (mapeable a 403). INV-8.
- [ ] T074 [P] [US2] Test `test_accept_request_not_found_when_already_accepted` en `backend/tests/unit/test_friends_service.py`: la fila ya está `accepted` → `accept_request` lanza `RequestNotFound` (la lógica filtra `status='pending'`). HD-7.
- [ ] T075 [P] [US2] Test `test_accept_request_not_found_when_requester_anonymized` en `backend/tests/unit/test_friends_service.py`: requester de la solicitud está anonimizado → `accept_request` lanza `RequestNotFound`. HD-5.
- [ ] T076 [P] [US2] Test `test_reject_request_deletes_row` en `backend/tests/unit/test_friends_service.py`: tras `reject_request(db, request_id, current_user=bob)`, la fila ya no existe; el resultado es `FriendRequestActionResult(action="rejected", relationship_status=SIN_RELACION)`. INV-7.
- [ ] T077 [P] [US2] Test `test_reject_request_forbidden_for_non_addressee` en `backend/tests/unit/test_friends_service.py`.
- [ ] T078 [P] [US2] Test `test_remove_friend_deletes_single_row_regardless_of_direction` en `backend/tests/unit/test_friends_service.py`: insertar `accepted_friendship_a_b` (requester=alice). `remove_friend(db, current_user=bob, target_user=alice)` borra la única fila (no la fila simétrica que no existe). INV-4 / HD-4.
- [ ] T079 [P] [US2] Test `test_remove_friend_404_when_no_accepted_friendship` en `backend/tests/unit/test_friends_service.py`: solo hay una fila `pending` → `remove_friend` lanza `FriendshipNotFound` (no toca la fila pending).
- [ ] T080 [P] [US2] Test `test_remove_friend_does_not_delete_pending_request` en `backend/tests/unit/test_friends_service.py`: con `pending_request_a_to_b`, `remove_friend(db, current_user=alice, target_user=bob)` → `FriendshipNotFound`; la fila pending sigue intacta.
- [ ] T081 [P] [US2] Test `test_list_received_requests_returns_pending_only_for_current_user` en `backend/tests/unit/test_friends_service.py`: con `pending_request_a_to_b` y otra solicitud no relacionada, `list_received_requests(db, current_user=bob)` devuelve solo la primera; con `current_user=alice` devuelve `[]`.
- [ ] T082 [P] [US2] Test `test_list_received_requests_filters_anonymized_requesters` en `backend/tests/unit/test_friends_service.py`: una solicitud cuyo requester está anonimizado no aparece en el listado. HD-5.

### Tests integración backend (Red) — en paralelo

- [ ] T083 [P] [US2] Test `test_post_friend_request_returns_201_and_persists` en `backend/tests/integration/test_friends_routes.py`: `POST /api/friends/request/{bob.id}` con alice autenticada → 201 con `FriendRequestResponse`; fila `pending` en BD.
- [ ] T084 [P] [US2] Test `test_post_friend_request_to_self_returns_400` en `backend/tests/integration/test_friends_routes.py`: `POST /api/friends/request/{alice.id}` con alice autenticada → 400 con detail "No puedes enviarte una solicitud a ti mismo." HD-7.
- [ ] T085 [P] [US2] Test `test_post_friend_request_to_unknown_user_returns_404` en `backend/tests/integration/test_friends_routes.py`: `user_id` UUID válido pero inexistente → 404. HD-7.
- [ ] T086 [P] [US2] Test `test_post_friend_request_to_anonymized_user_returns_404` en `backend/tests/integration/test_friends_routes.py`: addressee con `deleted_at` no nulo → 404. HD-5.
- [ ] T087 [P] [US2] Test `test_post_friend_request_returns_409_when_already_friends` en `backend/tests/integration/test_friends_routes.py`: con `accepted_friendship_a_b`, `POST .../request/{bob.id}` por alice → 409 con detail "Ya sois amigos."
- [ ] T088 [P] [US2] Test `test_post_friend_request_returns_409_when_pending_same_direction` en `backend/tests/integration/test_friends_routes.py`: con `pending_request_a_to_b`, alice reintenta → 409 con detail específico de "Ya tienes una solicitud pendiente con este usuario."
- [ ] T089 [P] [US2] Test `test_post_friend_request_returns_409_when_pending_cross_direction` en `backend/tests/integration/test_friends_routes.py`: con `pending_request_a_to_b`, bob intenta enviar a alice → 409 con detail "Este usuario ya te ha enviado una solicitud; acéptala desde tu panel." HD-3 (rama crítica).
- [ ] T090 [P] [US2] Test `test_post_accept_request_returns_200_and_marks_accepted` en `backend/tests/integration/test_friends_routes.py`: con `pending_request_a_to_b` autenticando como bob, `POST .../request/{request_id}/accept` → 200 con `relationship_status: "AMIGO"`.
- [ ] T091 [P] [US2] Test `test_post_accept_request_returns_403_when_not_addressee` en `backend/tests/integration/test_friends_routes.py`: alice intenta aceptar su propia solicitud → 403.
- [ ] T092 [P] [US2] Test `test_post_accept_request_returns_404_when_not_pending` en `backend/tests/integration/test_friends_routes.py`: la solicitud ya está `accepted` → 404.
- [ ] T093 [P] [US2] Test `test_post_reject_request_returns_200_and_deletes_row` en `backend/tests/integration/test_friends_routes.py`.
- [ ] T094 [P] [US2] Test `test_post_reject_request_returns_403_when_not_addressee` en `backend/tests/integration/test_friends_routes.py`.
- [ ] T095 [P] [US2] Test `test_delete_friend_returns_204_when_friends` en `backend/tests/integration/test_friends_routes.py`: con `accepted_friendship_a_b`, alice elimina a bob → 204; subsiguiente `GET /api/profile/bob` por alice devuelve `relationship_status: "SIN_RELACION"`.
- [ ] T096 [P] [US2] Test `test_delete_friend_returns_204_regardless_of_who_initiated` en `backend/tests/integration/test_friends_routes.py`: con `accepted_friendship_a_b` (requester=alice), bob (el addressee original) elimina a alice → 204. HD-4.
- [ ] T097 [P] [US2] Test `test_delete_friend_returns_404_when_no_accepted_friendship` en `backend/tests/integration/test_friends_routes.py`.
- [ ] T098 [P] [US2] Test `test_delete_friend_returns_404_when_only_pending_request_exists` en `backend/tests/integration/test_friends_routes.py`: la solicitud `pending` no se ve afectada y la respuesta es 404.
- [ ] T099 [P] [US2] Test `test_get_friends_requests_returns_received_pending` en `backend/tests/integration/test_friends_routes.py`: con `pending_request_a_to_b` autenticando como bob, `GET /api/friends/requests` → 200 con un elemento.
- [ ] T100 [P] [US2] Test `test_get_friends_requests_returns_empty_for_user_without_received` en `backend/tests/integration/test_friends_routes.py`: alice (que solo envió, no recibió) → 200 con `[]`.
- [ ] T101 [P] [US2] Test `test_concurrent_cross_requests_only_one_succeeds` en `backend/tests/integration/test_friends_routes.py`: simulación secuencial — alice envía a bob (esperar 201), bob envía a alice (esperar 409 con detail cruzado). INV-12 / HD-3.

### Tests frontend (Red) — en paralelo

- [ ] T102 [P] [US2] Test unitario `frontend/tests/unit/FriendshipButton.test.jsx::"renders Añadir amigo for SIN_RELACION"`: `<FriendshipButton status="SIN_RELACION" />` muestra texto "Añadir amigo" y está habilitado.
- [ ] T103 [P] [US2] Test unitario `frontend/tests/unit/FriendshipButton.test.jsx::"renders Pendiente disabled for PENDIENTE_ENVIADA"`: muestra "Pendiente" y está deshabilitado.
- [ ] T104 [P] [US2] Test unitario `frontend/tests/unit/FriendshipButton.test.jsx::"renders Aceptar/Rechazar inline for PENDIENTE_RECIBIDA"`: muestra dos acciones (aceptar y rechazar) o, alternativamente, un botón único que dispara la aceptación; el contrato exacto se decide en el componente, pero tiene que ser distinguible visualmente del estado `SIN_RELACION` y permitir disparar `onAccept`/`onReject`.
- [ ] T105 [P] [US2] Test unitario `frontend/tests/unit/FriendshipButton.test.jsx::"renders Eliminar amigo for AMIGO"`: muestra "Eliminar amigo".
- [ ] T106 [P] [US2] Test unitario `frontend/tests/unit/FriendshipButton.test.jsx::"calls onSendRequest when clicked in SIN_RELACION"`: con prop `onSendRequest` mock, click → llamada hecha.
- [ ] T107 [P] [US2] Test integración `frontend/tests/integration/UserProfile.test.jsx::"sends friend request and updates button to Pendiente"`: render con `relationship_status: "SIN_RELACION"`; click en "Añadir amigo"; MSW devuelve 201 y refetch del perfil devuelve `relationship_status: "PENDIENTE_ENVIADA"`; el botón pasa a "Pendiente".
- [ ] T108 [P] [US2] Test integración `frontend/tests/integration/UserProfile.test.jsx::"removes friend and updates button to Añadir amigo"`: render con `AMIGO`; click "Eliminar amigo" → 204 → refetch → "Añadir amigo".
- [ ] T109 [P] [US2] Test integración `frontend/tests/integration/UserProfile.test.jsx::"shows error toast on 409 conflict"`: MSW devuelve 409 al pulsar "Añadir amigo" (caso de race) → mensaje visible al usuario, botón vuelve al estado anterior.
- [ ] T110 [P] [US2] Test integración `frontend/tests/integration/UserSearchBar.test.jsx::"renders FriendshipButton inline per result"`: cada resultado de la búsqueda incluye un botón con el `relationship_status` correcto del backend.

### Implementation backend (Green)

- [ ] T111 [US2] Implementar `friends_service.send_request(db, requester_id: UUID, addressee_id: UUID) -> FriendRequestResponse` en `backend/app/services/friends_service.py`: (a) si `requester_id == addressee_id` → `SelfFriendRequest`; (b) SELECT user por `addressee_id` con `deleted_at IS NULL`; si no existe → `UserNotFound`; (c) BEGIN transacción; (d) `SELECT ... FOR UPDATE` con `OR` sobre las dos direcciones; (e) según el resultado, mapear a `FriendshipAlreadyExists` con `kind` apropiado o ejecutar `INSERT`; (f) COMMIT; (g) construir y devolver `FriendRequestResponse`. Verificar que T066-T071 pasan.
- [ ] T112 [US2] Implementar `friends_service.accept_request(db, request_id: UUID, current_user_id: UUID) -> FriendRequestActionResult` en `backend/app/services/friends_service.py`: (a) SELECT por `request_id` y `status='pending'`; si no → `RequestNotFound`; (b) si `addressee_id != current_user_id` → `NotRequestAddressee`; (c) verificar que el `requester` no está anonimizado (`deleted_at IS NULL`); si lo está → `RequestNotFound` (HD-5); (d) UPDATE `status='accepted'`; (e) devolver `FriendRequestActionResult(request_id, action="accepted", relationship_status=AMIGO)`. Verificar que T072-T075 pasan.
- [ ] T113 [US2] Implementar `friends_service.reject_request(db, request_id: UUID, current_user_id: UUID) -> FriendRequestActionResult` en `backend/app/services/friends_service.py`: precondiciones equivalentes a `accept_request` salvo paso (d) que es `DELETE`; devolver `FriendRequestActionResult(action="rejected", relationship_status=SIN_RELACION)`. Verificar que T076-T077 pasan.
- [ ] T114 [US2] Implementar `friends_service.remove_friend(db, current_user_id: UUID, target_user_id: UUID) -> None` en `backend/app/services/friends_service.py`: ejecuta el `DELETE FROM friendships WHERE status='accepted' AND ((requester_id=:a AND addressee_id=:b) OR (requester_id=:b AND addressee_id=:a)) RETURNING id`; si afecta 0 filas → `FriendshipNotFound`. Verificar que T078-T080 pasan.
- [ ] T115 [US2] Implementar `friends_service.list_received_requests(db, current_user_id: UUID) -> list[FriendRequestResponse]` en `backend/app/services/friends_service.py`: SELECT `friendships` JOIN `users` (alias `requester`) por `addressee_id=:current_user_id AND status='pending' AND requester.deleted_at IS NULL`; mapear a `FriendRequestResponse` (incluyendo `requester_nickname` y `requester_avatar_url`). Verificar que T081-T082 pasan.
- [ ] T116 [US2] Añadir ruta `POST /request/{user_id}` en `backend/app/api/routes/friends.py`: dependencias estándar; mapeo de excepciones a HTTP según HD-7 (`SelfFriendRequest → 400`, `UserNotFound → 404`, `FriendshipAlreadyExists → 409` con detail según `kind`); devuelve `FriendRequestResponse` 201. Verificar que T083-T089 pasan.
- [ ] T117 [US2] Añadir ruta `POST /request/{request_id}/accept` en `backend/app/api/routes/friends.py`: mapeo `RequestNotFound → 404`, `NotRequestAddressee → 403`; devuelve `FriendRequestActionResult` 200. Verificar que T090-T092 pasan.
- [ ] T118 [US2] Añadir ruta `POST /request/{request_id}/reject` en `backend/app/api/routes/friends.py`: análoga a accept. Verificar que T093-T094 pasan.
- [ ] T119 [US2] Añadir ruta `DELETE /{user_id}` en `backend/app/api/routes/friends.py`: mapeo `FriendshipNotFound → 404`; devuelve 204 sin body. Verificar que T095-T098 pasan.
- [ ] T120 [US2] Añadir ruta `GET /requests` en `backend/app/api/routes/friends.py`: invoca `list_received_requests`; devuelve `list[FriendRequestResponse]`. Verificar que T099-T100 pasan y que el `401` del foundational T015 se sostiene.
- [ ] T121 [US2] Verificar T101 (race A↔B) ejecutando los dos POST secuencialmente con autenticaciones distintas y comprobando los detail correctos en el 409.

### Implementation frontend (Green)

- [ ] T122 [P] [US2] Extender `frontend/src/api/friendsApi.js` con `sendRequest(userId)` (POST), `acceptRequest(requestId)` (POST), `rejectRequest(requestId)` (POST), `removeFriend(userId)` (DELETE), y `getReceivedRequests()` (GET, expuesto pero no consumido por UI esta fase). Todas con `credentials: "include"` y `Content-Type: application/json` cuando aplique.
- [ ] T123 [P] [US2] Crear `frontend/src/components/FriendshipButton.jsx`: recibe `{ status, onSendRequest, onAccept, onReject, onRemove }` por props; renderiza un único botón cuyo texto y comportamiento dependen de `status` (HD-1):
  - `SIN_RELACION` → "Añadir amigo" habilitado, click → `onSendRequest`.
  - `PENDIENTE_ENVIADA` → "Pendiente" deshabilitado, sin handler.
  - `PENDIENTE_RECIBIDA` → muestra "Aceptar" (primario) y "Rechazar" (secundario) inline; click → `onAccept` / `onReject`.
  - `AMIGO` → "Eliminar amigo", click → `onRemove`. Verificar que T102-T106 pasan.
- [ ] T124 [US2] Wirear `<FriendshipButton />` en `frontend/src/pages/UserProfile.jsx`: tras pulsar cualquier acción, refetch del perfil con `getPublicProfile` para que el `relationship_status` reflejado en el botón venga del backend (HD-1). Manejo de errores 409 con un mensaje visible (toast inline). Verificar que T107-T109 pasan.
- [ ] T125 [US2] Wirear `<FriendshipButton />` en `frontend/src/components/UserSearchResult.jsx`: cada fila incluye su botón con el `relationship_status` que vino del backend; al pulsar, refetch del listado actual de la búsqueda para reflejar los nuevos estados. Verificar que T110 pasa.
- [ ] T126 [P] [US2] Extender `frontend/tests/mocks/friendsHandlers.js` con handlers para `POST /api/friends/request/:user_id` (201/400/404/409 según el `user_id`/contexto), `POST /api/friends/request/:request_id/accept` (200/403/404), `POST /api/friends/request/:request_id/reject` (200/403/404), `DELETE /api/friends/:user_id` (204/404), `GET /api/friends/requests` (200 con varias colecciones-fixture). Registrar/actualizar en `frontend/tests/mocks/server.js`.

**Checkpoint**: US2 funcional. El usuario puede enviar/aceptar/rechazar/eliminar amistades, con el estado del botón reflejado en backend en cada vista. Cumple SC-004, SC-005, SC-006, SC-007, SC-008.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Validación end-to-end, cobertura, lint y smoke tests manuales.

- [ ] T127 [P] Ejecutar `pytest --cov=app --cov-report=term-missing` desde `backend/`. Verificar que la cobertura de los módulos nuevos (`friends_service.py`, `routes/friends.py`, `schemas/friends.py`, `models/friendship.py`) y de las extensiones (`profile_service.get_public_profile`, `routes/profile.py::GET /{nickname}`) está al menos a la altura de la base heredada de 003.
- [ ] T128 [P] Ejecutar `npm run test:run` desde `frontend/`: todos los archivos en verde, incluidos `FriendshipButton.test.jsx`, `UserSearchBar.test.jsx`, `UserProfile.test.jsx`.
- [ ] T129 [P] Ejecutar `ruff check backend/` y corregir warnings (si está disponible en el entorno; si no, queda registrado para una iteración futura, igual que en 003).
- [ ] T130 Ejecutar manualmente los smoke tests 5.1 a 5.8 de [quickstart.md](./quickstart.md) con un backend conectado a PostgreSQL real y dos o tres usuarios sembrados (`alice`, `bob`, `carl`). Documentar cualquier desviación.
- [ ] T131 Verificar que la migración Alembic es reversible: `alembic downgrade -1` debe eliminar la tabla `friendships` y el tipo `friendship_status` sin error; `alembic upgrade head` debe restaurarlos.
- [ ] T132 [P] Verificar manualmente (o con un test puntual) que el endpoint `GET /api/friends/requests` devuelve los datos correctos pese a no tener UI asociada en esta fase: `curl --cookie "access_token=..."` con dos usuarios sembrados y una solicitud pendiente.
- [ ] T133 [P] `CLAUDE.md` ya fue actualizado por `update-agent-context.ps1` durante `/speckit.plan`; entrada de 004 presente con la nota sobre la nueva tabla `friendships`. Verificar y, si falta, ejecutar de nuevo `.specify/scripts/powershell/update-agent-context.ps1 -AgentType claude`.
- [ ] T134 Cerrar la feature: actualizar `Status` de la spec a "Implemented" y abrir PR. Confirmar que los 4 bloques del checklist `requirements.md` siguen pasando.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sin dependencias — puede empezar inmediatamente.
- **Foundational (Phase 2)**: Depende de Setup. **BLOQUEA** todas las user stories.
- **User Stories (Phases 3-4)**: Dependen de Foundational completa. Cada una es independientemente testeable.
  - **US1 (P1)** entrega valor por sí sola: el usuario puede buscar a otros y ver su perfil.
  - **US2 (P2)** depende del valor de US1 a nivel de UX (sin perfil ajeno no hay punto natural para pulsar el botón), pero a nivel de backend sus endpoints son independientes y pueden testearse aisladamente. **Recomendación**: completar US1 antes de US2 para preservar la coherencia del MVP.
- **Polish (Phase 5)**: Depende de las user stories deseadas para esa entrega.

### Within Each User Story

- Tests (Red) **DEBEN** fallar antes de la implementación (Principio II).
- Modelos antes que servicios (en Foundational).
- Servicios antes que rutas.
- Backend antes de Frontend (los handlers MSW del frontend imitan el contrato HTTP).
- Story completa antes de pasar a la siguiente prioridad.

### Parallel Opportunities

- **Setup**: T002 y T003 pueden ejecutarse en paralelo.
- **Foundational tests**: T004-T015 todos `[P]`, en ficheros distintos.
- **Foundational implementation**: T018, T019, T023 pueden trabajarse en paralelo con T016-T017 (tras Alembic). T020 depende de T016-T018.
- **US1 tests**: T024-T053 todos `[P]`.
- **US1 implementation**: T058-T065 frontend pueden trabajarse en paralelo con T054-T057 backend; el cableado final (T063, T065) cierra la story.
- **US2 tests**: T066-T110 todos `[P]`.
- **US2 implementation**: T111-T115 (servicios) → T116-T120 (rutas) son secuenciales por archivo (`friends_service.py`, `friends.py`); T122-T123, T126 frontend pueden trabajarse en paralelo con backend a partir de T116; T124-T125 dependen de T123 y de un backend funcional.
- Si hay equipo de 2 personas: tras Foundational, Dev A completa US1; Dev B avanza el modelo mental de US2 leyendo plan/research y prepara los handlers MSW. Tras US1 mergeada, Dev B aterriza US2.

---

## Parallel Example: User Story 1

```bash
# Tests Red en paralelo (US1):
pytest backend/tests/unit/test_friends_service.py::test_search_excludes_self
pytest backend/tests/unit/test_friends_service.py::test_search_is_case_insensitive
pytest backend/tests/unit/test_friends_service.py::test_search_limited_to_20_results

pytest backend/tests/integration/test_friends_routes.py::test_friends_search_returns_results_with_relationship_status
pytest backend/tests/integration/test_profile_routes.py::test_get_public_profile_returns_200_for_existing_user

# Frontend en paralelo:
npm --prefix frontend run test -- UserSearchBar.test.jsx
npm --prefix frontend run test -- UserProfile.test.jsx
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Phase 1 (Setup) y Phase 2 (Foundational).
2. Completar Phase 3 (US1).
3. **STOP y VALIDAR**: smoke tests 5.1-5.2 de [quickstart.md](./quickstart.md).
4. Demo / merge si listo. Esto ya entrega valor: el usuario puede descubrir a otros y ver sus perfiles públicos.

### Incremental Delivery

1. Setup + Foundational → fundación lista.
2. US1 → demo, merge → MVP (descubrimiento).
3. US2 → demo, merge → relaciones de amistad operativas a nivel API y UI (sin panel principal).
4. Polish.

### Parallel Team Strategy

- Tras Foundational:
  - Dev A: US1 (search + perfil ajeno + UserSearchBar + UserProfile).
  - Dev B: US2 (FriendshipButton + endpoints de envío/aceptación/rechazo/eliminación).
- Conflictos esperados:
  - Ediciones concurrentes de `frontend/src/pages/UserProfile.jsx` (T062 en US1, T124 en US2) y `frontend/tests/mocks/friendsHandlers.js` (T064 en US1, T126 en US2). Coordinar via PRs encadenados o un único PR de "wiring final".
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
