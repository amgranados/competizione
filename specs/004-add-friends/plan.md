# Implementation Plan: Añadir amigos

**Branch**: `004-add-friends` | **Date**: 2026-04-28 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-add-friends/spec.md`
**Stack input (humano)**: `prompts/second/04-amigo.txt` — el humano fija stack, librerías, restricciones y estructura de carpetas. Este plan lo asume sin cuestionarlo (Constitución IV). La carpeta `prompts/` es **input histórico**, no referenciado en runtime (Constitución V).

## Summary

Sección de amigos para usuarios autenticados con tres flujos funcionales: (1) búsqueda parcial e insensible a mayúsculas de usuarios por nickname (excluyendo al propio), limitada a 20 resultados; (2) visualización del perfil de otro usuario reutilizando el `GET /api/profile` ya existente en 003 mediante una variante "público" que omite los controles de edición; (3) gestión de la relación de amistad mediante un único botón contextual con estado calculado en backend (`SIN_RELACION` / `PENDIENTE_ENVIADA` / `PENDIENTE_RECIBIDA` / `AMIGO`). Backend Python/FastAPI expone endpoints REST bajo `/api/friends/*` siguiendo la nomenclatura del prompt; frontend React (Vite) consume la API con `fetch` nativo y `credentials: "include"`. **No hay nuevas dependencias runtime ni test-only** respecto a 003 — todo lo necesario ya está instalado. Se añade una única tabla nueva `friendships` con `(id, requester_id, addressee_id, status, created_at)` y constraints que impiden duplicados y solicitudes cruzadas (HD-3). El endpoint `GET /api/friends/requests` queda implementado pero **sin UI asignada** en esta iteración (consumido por una futura iteración del panel principal).

## Technical Context

**Language/Version**: Backend **Python ≥3.12**. Frontend **Node ≥20 (LTS)** para Vite.

**Primary Dependencies** (todas heredadas; sin altas):
- Backend runtime: **FastAPI**, **SQLAlchemy 2.x async**, **Alembic**, **Pydantic v2**, **pydantic-settings**, **PyJWT + passlib[bcrypt]** (heredados de 001 para autenticación), **httpx** (heredado; no se usa en el flujo de amigos pero sigue presente para el resto del proyecto), `python-multipart>=0.0.9`, `slowapi` (herencia 001).
- Backend tests: **pytest**, **pytest-asyncio**, **httpx** (test client FastAPI), **pytest-cov**. Sin necesidad de `respx` aquí (no hay llamadas externas en este flujo).
- Frontend runtime: **React 18 + React Router v6**, `fetch` nativo con `credentials: "include"` (sin axios, sin localStorage).
- Frontend tests: **Vitest**, `@testing-library/react`, `@testing-library/user-event`, **msw**.
- **Sin librerías nuevas**: el flujo es CRUD puro sobre una tabla nueva.

**Storage**: **PostgreSQL 15+** vía SQLAlchemy async; migraciones con Alembic. Esta iteración añade una tabla `friendships` y **no modifica** ninguna tabla existente. El esquema de 001 (`users`, `token_blacklist`), 002 (`tournaments`, `participants`, `invitations`, `matches`, `notifications`) y 003 (`riot_accounts` + columnas `users.avatar_url`, `users.deleted_at`) se conserva intacto. La búsqueda hace `ILIKE %q%` sobre `users.nickname` con filtro `deleted_at IS NULL`.

**Testing**:
- **Principio II (NO NEGOCIABLE)**: todo código productivo nace de un test fallido (Red → Green → Refactor). Detalle TDD en `research.md § TDD Workflow`.
- Tests unitarios específicos: `test_friends_service.py` (exclusión del propio usuario, límite de 20, duplicidad en ambas direcciones, eliminación bidireccional, cálculo de estado de relación).
- Tests de integración: `test_friends_routes.py` (cubre cada endpoint con casos felices y de error, incluido el flujo cruzado A→B vs B→A).
- Tests frontend: `FriendshipButton.test.jsx` (unit, renderizado por estado), `UserSearchBar.test.jsx` y `UserProfile.test.jsx` (integración con MSW).

**Target Platform**: Servidor Linux en producción; HTTPS obligatorio (cookies `Secure=True` heredadas de 001). El frontend es SPA servida desde Vite-build estática.

**Project Type**: **Backend API + Frontend SPA separados** (mismo layout que 001/002/003). Estructura fijada literalmente por el prompt.

**Performance Goals**: SC-001 fija que los resultados de búsqueda lleguen en **<2 s** en condiciones normales. Como la consulta es un `ILIKE %q%` sin índice trigram, en un volumen moderado (< 10k usuarios) el seq-scan filtrado por `deleted_at IS NULL` es aceptable; el límite hard de 20 resultados protege la respuesta. SC-006 fija que tras aceptar una solicitud el botón en ambos lados refleje "Eliminar amigo" en **<5 s**: el botón se calcula del lado servidor con cada `GET /api/profile/{nickname}` o cada elemento de la lista, así que el tiempo lo determina la latencia normal del request, no caché compartida.

**Constraints**:
- **Búsqueda**: case-insensitive, coincidencia parcial (`ILIKE %q%`), máximo 20 resultados, excluye al usuario autenticado y a usuarios anonimizados (`deleted_at IS NOT NULL`), exige `q` no vacío tras `strip()`.
- **Estado de relación calculado en backend**: el frontend no debe inferirlo; cada respuesta de búsqueda y cada `GET /api/profile/{nickname}` incluye el campo `relationship_status` con uno de `SIN_RELACION`, `PENDIENTE_ENVIADA`, `PENDIENTE_RECIBIDA`, `AMIGO`. (HD-1.)
- **No duplicar relaciones**: una solicitud de A → B se rechaza con `409` si ya existe `(A,B)` o `(B,A)` en estado `pending` o `accepted` (HD-3).
- **Eliminación bidireccional**: `DELETE /api/friends/{user_id}` borra la fila `accepted` única que une a los dos usuarios; ambos lados pierden la amistad simultáneamente (HD-4).
- **Auto-amistad imposible**: `POST /api/friends/request/{user_id}` con `user_id == current_user.id` → `400 Bad Request` (FR-014).
- **Solicitud cruzada simultánea**: la primera en alcanzar el `INSERT` gana; la segunda recibe `409`. La aceptación de cualquiera de las dos solo materializa una amistad porque la relación es simétrica y los constraints lo garantizan (HD-3).
- **Anonimización (003)**: si A es amigo de B y B se anonimiza (`deleted_at` no nulo), la fila de `friendships` queda con `addressee` o `requester` apuntando a un usuario "deleted-XXXX". A nivel de presentación, el frontend muestra el nickname anonimizado tal cual lo trae `users.nickname` y NO se ofrece botón "Eliminar amigo" sobre un perfil de un usuario anonimizado (porque no se puede navegar a su perfil — la búsqueda lo excluye). El backend, sin embargo, sí devolverá la amistad si el usuario activo lo busca con un endpoint de "mis amigos" (no en alcance esta iteración). FR-020 se cumple soft: el listado público de amigos no es objeto de esta iteración. (HD-5.)
- **Cookies HttpOnly/Secure/SameSite=lax** (001) y endpoints autenticados (FR-019): toda llamada a `/api/friends/*` exige sesión válida.
- **Sin nuevas variables de entorno**.

**Scale/Scope**: Primera versión. Volumen estimado: una búsqueda dispara una consulta indexada por `nickname` (índice ya existente en 001 por unicidad); el cálculo de `relationship_status` por cada resultado es un único `LEFT JOIN` lateral sobre `friendships` filtrando por `requester_id` o `addressee_id` del usuario autenticado. Sin SLA fijado.

## Scope de la iteración actual

Derivado de `spec.md` y del prompt de stack. **Reglas claras** para evitar ambigüedades.

### ✅ Implementado esta iteración

| Área | Funcionalidad | FR cubiertos |
|------|---------------|--------------|
| Búsqueda de usuarios | `GET /api/friends/search?q=` con `ILIKE %q%`, case-insensitive, exclusión del propio usuario, límite 20, exclusión de anonimizados, vacío → `[]` | FR-001, FR-002, FR-003, FR-004 |
| Resultado interactivo | Cada elemento incluye `id`, `nickname`, `avatar_url` y `relationship_status`; el frontend lo enlaza al perfil ajeno | FR-005 |
| Visualización de perfil ajeno | `GET /api/profile/{nickname}` (variante "público" del endpoint propio); reutiliza la composición de 003 sin controles de edición | FR-006, FR-007, FR-008 |
| Botón contextual de relación | `FriendshipButton.jsx` reutilizable: estados `Añadir amigo` / `Pendiente` / `Eliminar amigo`. El estado lo dicta el backend (`relationship_status`) | FR-009, FR-010, FR-011, FR-012 |
| Enviar solicitud | `POST /api/friends/request/{user_id}` con duplicidad bloqueada en BD vía SELECT FOR UPDATE + UNIQUE constraint | FR-010, FR-013 |
| Bloqueo de auto-solicitud | El propio user_id se rechaza con `400` | FR-014 |
| Aceptar / rechazar | `POST /api/friends/request/{request_id}/accept` y `/reject` consumen la solicitud y, en el caso de aceptar, dejan la fila en estado `accepted` | FR-015, FR-016, FR-017 |
| Eliminar amistad | `DELETE /api/friends/{user_id}` borra la única fila `accepted` que une a ambos | FR-012, FR-018 |
| Listar solicitudes recibidas (API only) | `GET /api/friends/requests` devuelve solicitudes recibidas pendientes; **sin UI** | FR-015 |
| Seguridad transversal | Endpoints autenticados; nunca actúan en nombre de otro usuario; usuarios anonimizados nunca aparecen en búsqueda ni reciben solicitudes | FR-019 |

### ⚠️ Fuera de alcance esta iteración (diferido)

| Área | Motivo | Reentrada |
|------|--------|-----------|
| UI del panel principal con solicitudes recibidas | El prompt declara: "El endpoint GET /friends/requests existe y devuelve las solicitudes recibidas pendientes. No tiene UI asignada en esta fase." | Iteración futura del panel principal. |
| Listado público "mis amigos" / "amigos de X" | No exigido por la spec ni por el prompt. | Cuando se vincule la integración con torneos (invitar amigos a un torneo). |
| Notificaciones tipo "X te envió solicitud" | El prompt no lo pide; 002 ya tiene infra de notificaciones, pero no se cablea aquí. | Cuando se diseñe la UI del panel principal. |
| Bloquear usuario / lista negra | Spec declara explícitamente "queda fuera de alcance". | Iteración futura si surge la necesidad. |
| Caducidad de solicitudes pendientes | Spec asume que no caducan. | Solo si se observa abuso o ruido en el inbox. |

### 🟢 Decisiones humanas resueltas al planificar

| Tema | Decisión humana (2026-04-28) |
|------|-------------------------------|
| Cálculo del estado de relación | El backend lo calcula y lo devuelve **en cada respuesta** que tenga sentido (resultado de búsqueda, perfil ajeno). El frontend no consulta una "tabla de estados" aparte. (HD-1) |
| Modelo de tabla `friendships` | Una sola fila por relación (sin duplicados simétricos): `(requester_id, addressee_id)` con UNIQUE. El status `accepted` representa amistad bidireccional; el status `pending` representa solicitud direccional. La eliminación de amistad borra la fila. La aceptación reaprovecha la fila existente (no crea dos). (HD-2) |
| Detección de duplicidad en cualquier dirección | Antes de insertar, `SELECT ... FOR UPDATE WHERE (requester_id=A AND addressee_id=B) OR (requester_id=B AND addressee_id=A)` dentro de la transacción. Si existe en `pending` o `accepted` → `409 Conflict`. Garantiza atomicidad ante solicitudes cruzadas A↔B simultáneas. (HD-3) |
| Eliminación bidireccional | `DELETE /api/friends/{user_id}` busca la única fila con status `accepted` que une a `current_user` y `user_id` en cualquier dirección y la borra. Una sola operación elimina la amistad para ambos lados. (HD-4) |
| Comportamiento ante usuarios anonimizados (003) | La búsqueda excluye usuarios con `deleted_at IS NOT NULL`. La aceptación/rechazo de una solicitud antigua donde el remitente fue anonimizado se trata como `404` (la solicitud "ya no es válida"). El cleanup explícito al anonimizar (forzar `DELETE` en filas de `friendships`) **no se hace en 004**: las solicitudes pendientes de o hacia un usuario anonimizado quedan huérfanas pero invisibles, y los endpoints filtran `deleted_at IS NULL` en cada extremo cuando es necesario. (HD-5) |
| Mínimo de longitud de búsqueda | Tras `strip()`, longitud ≥ 1. No se exige longitud mínima mayor (el prompt no lo pide). El límite hard de 20 resultados protege la respuesta. (HD-6) |
| Política de mensajes de error | Errores genéricos pero descriptivos: `400` (entrada inválida, auto-solicitud), `403` (no es destinatario de la solicitud al aceptar/rechazar), `404` (usuario o solicitud no existe), `409` (relación ya existente), `401` (sin sesión). Sin enmascarar deliberadamente — el flujo no maneja credenciales sensibles como 003 con Riot. (HD-7) |

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Evaluación frente a `.specify/memory/constitution.md` (v1.0.0, 2026-04-21).

### Pre-Phase 0

| Principio | Estado | Notas |
|-----------|--------|-------|
| I. Cybersecurity Focused | **OK** | Sin nuevas dependencias. Toda escritura está protegida por sesión y por validación de "usuario sobre sí mismo": `current_user.id` se compara con el `requester`/`addressee` de la solicitud antes de aceptar/rechazar/eliminar. La búsqueda no expone datos privados (solo `id`, `nickname`, `avatar_url`, `relationship_status`). El campo `email` NUNCA se devuelve en respuestas de `/api/friends/*`. |
| II. TDD First (NO NEGOCIABLE) | **OK** | Cada FR de esta iteración nace de un test fallido. Tests unitarios dedicados para `friends_service` (exclusión del self, límite, duplicidad cruzada, bidireccionalidad, cálculo de estado) y de integración para cada ruta. Orden Red → Green → Refactor explícito en `research.md § TDD Workflow`. |
| III. Human Ownership of Product | **OK** | Decisiones humanas (HD-1 a HD-7) se enumeran arriba, justificadas y trazables. Diagramas en `contracts/*.puml`. La estructura de carpetas, los nombres de endpoints y las restricciones técnicas vienen literalmente del prompt; el plan documenta el "cómo" sin desviarse. |
| IV. Simplicity: Don't reinvent the wheel | **OK** | Se reutilizan: middleware de autenticación 001, dependencia `get_current_user`, fixtures de usuarios (`tests/conftest.py`), patrón de servicio + ruta + esquema heredado de 002/003. **No hay** abstracciones nuevas: una tabla, un servicio, una ruta. |
| V. Ignore Prompts Folder | **OK** | `prompts/` es input histórico; ningún código productivo lo referencia. |

**Resultado pre-Phase 0**: **PASA**. No quedan decisiones abiertas para `/speckit.tasks`.

### Post-Phase 1 (re-check tras diseño)

El diseño de `friendships` es deliberadamente plano (una fila por relación) y evita la duplicación simétrica (que requeriría triggers o capas extra). El cálculo del `relationship_status` se hace en backend con un único subquery por usuario listado, sin `N+1`. Los endpoints siguen la misma convención de seguridad que 001/002/003. **PASA sin nuevas observaciones.**

## Project Structure

### Documentation (this feature)

```text
specs/004-add-friends/
├── plan.md                            # Este fichero (/speckit.plan)
├── research.md                        # Fase 0 — decisiones humanas, TDD workflow, contención de carreras
├── data-model.md                      # Fase 1 — Friendship (nueva), invariantes, query del estado
├── quickstart.md                      # Fase 1 — env vars, ejecución, smoke tests
├── contracts/
│   ├── friends.openapi.yaml           # Endpoints REST de amigos
│   ├── friendship-state-machine.puml  # Diagrama de estados de la relación A↔B
│   └── add-friend-flow.puml           # Diagrama de secuencia: búsqueda → solicitud → aceptación → eliminación
├── checklists/
│   └── requirements.md                # /speckit.specify
└── tasks.md                           # Fase 2 — /speckit.tasks (NO generado por /speckit.plan)
```

### Source Code (repository root)

Estructura fijada literalmente por `prompts/second/04-amigo.txt`. Los ficheros **heredados** (de 001, 002, 003) **no se tocan** salvo donde se indique. Los **nuevos de esta iteración** aparecen como **IN**.

```text
backend/
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── auth.py                          # heredado 001
│   │       ├── profile.py                       # AJUSTE: añadir GET /api/profile/{nickname} (variante público sin email/controles)
│   │       ├── friends.py                       # IN  (GET /search, POST /request/{user_id}, POST /request/{request_id}/accept|reject, DELETE /{user_id}, GET /requests)
│   │       ├── tournaments.py                   # heredado 002 — sin cambios
│   │       ├── matches.py                       # heredado 002 — sin cambios
│   │       └── notifications.py                 # heredado 002 — sin cambios
│   ├── core/
│   │   ├── config.py                            # sin cambios
│   │   └── security.py                          # heredado 001
│   ├── db/
│   │   ├── base.py                              # registra el modelo nuevo (Friendship)
│   │   └── migrations/                          # nueva revisión Alembic: crea friendships
│   ├── models/
│   │   ├── user.py                              # heredado 003 (no se toca)
│   │   ├── riot_account.py                      # heredado 003
│   │   ├── friendship.py                        # IN  (id, requester_id, addressee_id, status, created_at + UNIQUE / CHECK constraints)
│   │   ├── tournament.py                        # heredado 002
│   │   ├── participant.py                       # heredado 002
│   │   ├── invitation.py                        # heredado 002
│   │   ├── match.py                             # heredado 002
│   │   ├── notification.py                      # heredado 002
│   │   └── token_blacklist.py                   # heredado 001
│   ├── schemas/
│   │   ├── auth.py                              # heredado 001
│   │   ├── profile.py                           # AJUSTE: añadir PublicProfileResponse (perfil ajeno + relationship_status)
│   │   ├── friends.py                           # IN  (UserSearchResult, FriendshipStatus enum, FriendRequestResponse, FriendRequestActionResult)
│   │   ├── tournament.py                        # heredado 002
│   │   ├── match.py                             # heredado 002
│   │   └── notification.py                      # heredado 002
│   ├── services/
│   │   ├── auth_service.py                      # heredado 001
│   │   ├── profile_service.py                   # AJUSTE: añadir get_public_profile(nickname, current_user) que reutiliza la composición LoL pero sin permisos de edición
│   │   ├── friends_service.py                   # IN  (search_users, send_request, accept_request, reject_request, remove_friend, list_received_requests, compute_relationship_status)
│   │   ├── tournament_service.py                # heredado 002
│   │   ├── match_service.py                     # heredado 002
│   │   ├── calendar_service.py                  # heredado 002
│   │   ├── standings_service.py                 # heredado 002
│   │   └── riot_api/                            # heredado 003 — sin cambios
│   └── main.py                                  # AJUSTE: registrar /api/friends
├── tests/
│   ├── conftest.py                              # AJUSTE: fixture de pareja de usuarios (alice/bob) y de relación pre-existente (pending/accepted)
│   ├── helpers.py                               # heredado 002
│   ├── unit/
│   │   ├── test_security.py                     # heredado 001
│   │   ├── test_auth_service.py                 # heredado 001
│   │   ├── test_calendar_service.py             # heredado 002
│   │   ├── test_standings_service.py            # heredado 002
│   │   ├── test_match_service.py                # heredado 002
│   │   ├── test_profile_service.py              # heredado 003 (no se toca; el endpoint público usa la misma lógica)
│   │   ├── test_friends_service.py              # IN  (exclusión del self, límite 20, duplicidad cruzada, eliminación bidireccional, cálculo de estado)
│   │   └── test_riot_api_client.py              # heredado 003
│   └── integration/
│       ├── test_auth_routes.py                  # heredado 001
│       ├── test_tournament_routes.py            # heredado 002
│       ├── test_match_routes.py                 # heredado 002
│       ├── test_notifications_routes.py         # heredado 002
│       ├── test_profile_routes.py               # AJUSTE: tests para GET /api/profile/{nickname} (existe / no existe / sin sesión / anonimizado)
│       └── test_friends_routes.py               # IN  (cubre los 6 endpoints con casos felices y de error, incluido cruzado A↔B y race-condition simulada con dos requests secuenciales pero coherentes)
└── requirements.txt                             # sin cambios

frontend/
├── src/
│   ├── api/
│   │   ├── authApi.js                           # heredado 001
│   │   ├── profileApi.js                        # AJUSTE: añadir getPublicProfile(nickname)
│   │   ├── friendsApi.js                        # IN  (searchUsers, sendRequest, acceptRequest, rejectRequest, removeFriend; getReceivedRequests está expuesto pero no usado por UI esta fase)
│   │   ├── tournamentApi.js                     # heredado 002
│   │   ├── matchApi.js                          # heredado 002
│   │   └── notificationApi.js                   # heredado 002
│   ├── context/
│   │   ├── AuthContext.jsx                      # heredado 001
│   │   └── NotificationContext.jsx              # heredado 002
│   ├── hooks/
│   │   ├── useAuth.js                           # heredado 001
│   │   ├── usePolling.js                        # heredado 002
│   │   └── useTournament.js                     # heredado 002
│   ├── components/
│   │   ├── ProtectedRoute.jsx                   # heredado 001
│   │   ├── ProfileForm.jsx                      # heredado 003
│   │   ├── LinkedGames.jsx                      # heredado 003
│   │   ├── LoLStats.jsx                         # heredado 003 (reutilizado en UserProfile.jsx)
│   │   ├── DeleteAccountModal.jsx               # heredado 003
│   │   ├── UserSearchBar.jsx                    # IN  (input controlado + dropdown de resultados; debounced fetch a /api/friends/search)
│   │   ├── UserSearchResult.jsx                 # IN  (fila clicable con avatar, nickname y FriendshipButton inline)
│   │   ├── FriendshipButton.jsx                 # IN  (un botón con tres estados visibles: "Añadir amigo" / "Pendiente" / "Eliminar amigo"; "Pendiente" es disabled)
│   │   ├── TournamentBracket.jsx                # heredado 002
│   │   └── StandingsTable.jsx                   # heredado 002
│   ├── pages/
│   │   ├── Login.jsx                            # heredado 001
│   │   ├── Register.jsx                         # heredado 001
│   │   ├── Dashboard.jsx                        # heredado 002 (mantiene su rol; la UI de solicitudes recibidas NO se añade aquí esta fase)
│   │   ├── TournamentDetail.jsx                 # heredado 002
│   │   ├── MatchDetail.jsx                      # heredado 002
│   │   ├── Profile.jsx                          # heredado 003 (perfil propio)
│   │   └── UserProfile.jsx                      # IN  (perfil de otro usuario; reutiliza LoLStats; sin opciones de edición; integra FriendshipButton)
│   └── main.jsx                                 # AJUSTE: ruta `/users/:nickname` protegida que monta UserProfile.jsx; punto de entrada visual del UserSearchBar (en header global o en una página de búsqueda — decisión visual no contractual)
└── tests/
    ├── setup.js                                 # heredado 001
    ├── mocks/
    │   ├── server.js                            # AJUSTE: registrar friendsHandlers
    │   ├── authHandlers.js                      # heredado 001
    │   ├── tournamentHandlers.js                # heredado 002
    │   ├── matchHandlers.js                     # heredado 002
    │   ├── profileHandlers.js                   # AJUSTE: añadir handler para GET /api/profile/:nickname
    │   └── friendsHandlers.js                   # IN  (mock de /api/friends/*)
    ├── unit/
    │   ├── useAuth.test.js                      # heredado 001
    │   ├── usePolling.test.js                   # heredado 002
    │   ├── ProfileForm.test.jsx                 # heredado 003
    │   └── FriendshipButton.test.jsx            # IN  (renderiza correctamente "Añadir amigo" / "Pendiente" / "Eliminar amigo" según prop `status`)
    └── integration/
        ├── Login.test.jsx                       # heredado 001
        ├── Register.test.jsx                    # heredado 001
        ├── ProtectedRoute.test.jsx              # heredado 001
        ├── TournamentDetail.test.jsx            # heredado 002
        ├── MatchDetail.test.jsx                 # heredado 002
        ├── Profile.test.jsx                     # heredado 003
        ├── DeleteAccountModal.test.jsx          # heredado 003
        ├── UserSearchBar.test.jsx               # IN  (escribir → ver resultados; clic → navegar al perfil)
        └── UserProfile.test.jsx                 # IN  (perfil ajeno con FriendshipButton funcional; transiciones de estado tras pulsar)
```

**Structure Decision**: Variante B (API + SPA) con la estructura literal del prompt. No se añaden carpetas ni ficheros fuera de esa lista, salvo los generados por Alembic dentro de `backend/app/db/migrations/`. La nueva ruta de perfil ajeno se añade en `profile.py` (mismo router que el perfil propio) en lugar de en `friends.py` para mantener una única definición canónica de "qué información es un perfil" (Constitución IV) — el botón de relación se inyecta como campo derivado, no como recurso aparte.

## Decisiones humanas resueltas (trazabilidad)

### Resueltas

| Decisión | Fuente | Resumen |
|----------|--------|---------|
| Stack fijado | prompt `04-amigo.txt` | Python/FastAPI + React/Vite + PostgreSQL/SQLAlchemy async + Alembic + pytest/Vitest. |
| Búsqueda case-insensitive y parcial | prompt | `ILIKE %q%` |
| Límite hard de 20 resultados | prompt | LIMIT 20 en SQL. |
| Exclusión del self | prompt + spec FR-002 | `WHERE user_id != current_user.id`. |
| Duplicidad bloqueada en backend | prompt | `SELECT FOR UPDATE` + UNIQUE constraint. |
| Eliminación bidireccional | prompt | Una fila por amistad; DELETE simétrico. |
| Estados calculados en backend | prompt | `relationship_status` viaja en cada respuesta relevante. |
| HD-1: estado calculado en respuesta | resuelto en plan 2026-04-28 | Sin endpoint dedicado de "consultar estado"; viene incrustado. |
| HD-2: una sola fila por relación | resuelto en plan 2026-04-28 | `friendships` usa el par `(requester_id, addressee_id)` y no duplica simétricamente. |
| HD-3: detección de duplicidad cruzada | resuelto en plan 2026-04-28 | `SELECT FOR UPDATE` con OR sobre ambas direcciones dentro de una transacción. |
| HD-4: eliminación bidireccional | resuelto en plan 2026-04-28 | Una fila → un DELETE → ambos lados pierden la amistad. |
| HD-5: usuarios anonimizados | resuelto en plan 2026-04-28 | Excluidos de búsqueda; solicitudes hacia ellos se vuelven invisibles. |
| HD-6: mínimo de búsqueda | resuelto en plan 2026-04-28 | `len(q.strip()) >= 1`. |
| HD-7: política de errores HTTP | resuelto en plan 2026-04-28 | 400/401/403/404/409 con mensajes claros. |

### Pendientes

> Ninguna. Todas las decisiones están resueltas antes de `/speckit.tasks`.

## Complexity Tracking

> Sin violaciones de la Constitución. Toda decisión estructural viene del humano.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (ninguna) | — | — |

La única "complejidad" añadida (transacción + `SELECT FOR UPDATE` para evitar duplicados cruzados) está justificada por la spec (FR-013, FR-021) y por el prompt ("validado en backend"); cualquier alternativa más sencilla (UNIQUE constraint solo en `(requester_id, addressee_id)`) deja la carrera A↔B sin resolver.
