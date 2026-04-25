# Implementation Plan: Editar perfil de usuario

**Branch**: `003-edit-profile` | **Date**: 2026-04-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-edit-profile/spec.md`
**Stack input (human)**: `prompts/second/03-perfil.txt` — el humano fija stack, librerías, restricciones y estructura de carpetas. Este plan lo asume sin cuestionarlo (Constitución IV). La carpeta `prompts/` es **input histórico**, no referenciado en runtime (Constitución V).

## Summary

Sección "Perfil" para usuarios autenticados con cuatro flujos: edición de nickname, edición de contraseña, edición de avatar (foto de perfil como URL), y vinculación/desvinculación de cuenta de League of Legends + visualización de datos públicos (nivel, servidor, Ranked Solo/Dúo, Ranked Flex, maestría de campeones y últimas 5 partidas). Incluye además la eliminación irreversible de la cuenta con confirmación textual exacta y bloqueo si el usuario participa en torneos activos. Backend Python/FastAPI expone endpoints REST bajo `/api/profile/*`; frontend React (Vite) consume la API con `fetch` nativo y `credentials: "include"`. La integración con la **Riot API ahora entra en runtime** (FR diferidos por 002 que se desbloquean): se implementa `HttpRiotAPIClient` con `httpx`, se extiende el `Protocol` `RiotAPIClient` con los nuevos métodos del prompt, y `MockRiotAPIClient` cubre dev/tests cuando `RIOT_API_KEY` no esté definida. Las **credenciales del videojuego (Riot ID)** se usan solo para resolver el PUUID y se descartan; lo único que se persiste es el PUUID y la región (entidad `RiotAccount`). Los datos de LoL se consultan **en tiempo real en cada carga del perfil** (sin caché), conforme al prompt. La foto de perfil se almacena como **URL** validada con `HttpUrl` de Pydantic; **no hay subida ni recorte de archivos en backend** esta iteración (la responsabilidad recae en quien hospede la imagen). El bloqueo de desvinculación reactiva el FR-004 que 002 dejó diferido.

## Technical Context

**Language/Version**: Backend **Python ≥3.12**. Frontend **Node ≥20 (LTS)** para Vite.

**Primary Dependencies** (todas fijadas por el prompt):
- Backend runtime: **FastAPI**, **SQLAlchemy 2.x async**, **Alembic**, **Pydantic v2** (uso explícito de `HttpUrl` para validar la URL de avatar), **pydantic-settings**, **httpx** (ya en `requirements.txt` desde 001/002; ahora pasa a uso productivo para la Riot API), **PyJWT + passlib[bcrypt]** heredados de 001, `python-multipart>=0.0.9`, `slowapi` (herencia 001).
- Backend tests: **pytest**, **pytest-asyncio**, **httpx** (test client FastAPI), **pytest-cov**, **respx** (**nueva**: mock de `httpx` para los tests del cliente HTTP de Riot — desbloquea la dependencia diferida en 002).
- Frontend runtime: **React 18 + React Router v6**, `fetch` nativo con `credentials: "include"` (sin axios, sin localStorage). Sin librerías de "image cropper" porque el prompt no las pide y la subida/recorte queda fuera del backend.
- Frontend tests: **Vitest**, `@testing-library/react`, `@testing-library/user-event`, **msw**.
- **Sin librerías nuevas** para validación de contraseña (re-uso de las reglas de 001-user-auth).

**Storage**: **PostgreSQL 15+** vía SQLAlchemy async; migraciones con Alembic. Esta iteración añade la tabla `riot_accounts` y dos columnas a `users` (`avatar_url`, opcionalmente nada más; ver `data-model.md`). El esquema de 001 (`users`, `token_blacklist`) y de 002 (`tournaments`, `participants`, `invitations`, `matches`, `notifications`) se conserva; las nuevas FK desde `riot_accounts.user_id` y la lectura cruzada con `participants` para los bloqueos no requieren cambios en tablas existentes.

**Testing**:
- **Principio II (NO NEGOCIABLE)**: todo código productivo nace de un test fallido (Red → Green → Refactor). Detalle TDD en `research.md § TDD Workflow`.
- Tests unitarios específicos: `test_profile_service.py` (unicidad de nickname, validación URL, restricciones de desvinculación, restricciones de eliminación, confirmación textual), `test_riot_api_client.py` (nuevo: HTTP client con `respx`, mock client con datos sembrados).
- Tests de integración: `test_profile_routes.py`, ampliaciones puntuales en `test_tournament_routes.py` si la lógica de bloqueo cruzado lo requiere (no esperado: el cruce vive en `profile_service`).
- Tests frontend: `ProfileForm.test.jsx` (unit), `Profile.test.jsx` y `DeleteAccountModal.test.jsx` (integración).

**Target Platform**: Servidor Linux en producción; HTTPS obligatorio (cookies `Secure=True` heredadas de 001). El frontend es SPA servida desde Vite-build estática. La Riot API se consume desde el backend (no desde el navegador) para evitar exponer la `RIOT_API_KEY` y por CORS.

**Project Type**: **Backend API + Frontend SPA separados** (mismo layout que 001/002). Estructura fijada literalmente por el prompt.

**Performance Goals**: No especificados de forma cuantitativa por el prompt. Indicativo, alineado con SC-007: el perfil con datos de LoL debe cargarse o caer en "no disponible" en **<5 s** en condiciones normales. Como no se cachea (decisión humana), el endpoint de perfil suma latencia de varias llamadas a Riot — se hacen **en paralelo** (ver `research.md § HD-3`) para mantenerse dentro del presupuesto.

**Constraints**:
- **Nickname único** validado en backend antes de persistir (FR-005).
- **Contraseña**: misma política de 001-user-auth (≥8 caracteres). Re-uso del validador existente.
- **Foto de perfil**: solo URL (`HttpUrl`). El backend NO descarga ni inspecciona el contenido; el peso/recorte recaen en quien hospede la imagen. Las cláusulas de spec FR-018, FR-019 quedan **declaradas fuera del alcance backend** y se reflejan en `spec.md` con la nota correspondiente (anotada en `research.md § Scope`).
- **Riot ID NUNCA se persiste**: solo se usa para llamar a `/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}`, obtener el PUUID y descartar las credenciales del videojuego. El PUUID y la región sí se persisten en `riot_accounts` (FR-012).
- **Mensaje de error genérico** si el Riot ID es inválido o las credenciales fallan (FR-013, SC-008): el backend devuelve **un único error** que no distingue causa.
- **Bloqueo de desvinculación**: si el usuario participa en al menos un torneo en estados `Inscripción abierta` o `En curso` para ese juego, no puede desvincular (FR-014; reactiva FR-004 de 002).
- **Bloqueo de eliminación de cuenta**: si el usuario participa en cualquier torneo `Inscripción abierta` o `En curso`, no puede eliminar la cuenta (FR-023).
- **Confirmación de eliminación**: el usuario debe escribir su **nickname actual** como cadena de confirmación (decisión HD-2 en `research.md`).
- **Datos de LoL en tiempo real, sin caché**: cada carga del perfil dispara las 4 llamadas Riot (perfil, ranked, maestría, partidas).
- **Cookies HttpOnly/Secure/SameSite=lax** (FR-025) heredadas de 001; tokens nunca expuestos a JS del navegador.
- **`RIOT_API_KEY`** ahora pasa a ser **operativa**: si está definida, se usa `HttpRiotAPIClient`; si no, `MockRiotAPIClient` con log explícito (mismo patrón que 002, ahora cableado).

**Scale/Scope**: Primera versión. Volumen estimado: el perfil se consulta a demanda; sin caché, una vista de perfil = 4 llamadas a Riot. Para un usuario con vista activa, el coste de Riot es bajo (Riot API permite 100 reqs/2 min en dev key). No hay SLA fijado.

## Scope de la iteración actual

Derivado de `spec.md` y del prompt de stack. **Reglas claras** para evitar ambigüedades.

### ✅ Implementado esta iteración

| Área | Funcionalidad | FR cubiertos |
|------|---------------|--------------|
| Sección "Perfil" | Página agregadora con datos básicos + juegos vinculados + opciones | FR-001, FR-002 |
| Edición de nickname | Cambio con validación de unicidad y mensaje de error claro; idempotencia si coincide con el actual | FR-004, FR-005, FR-006 |
| Edición de contraseña | Validación re-utilizando reglas 001; invalidación de sesiones distintas a la actual | FR-007, FR-008, FR-009 |
| Edición de avatar | Almacena URL validada con `HttpUrl`; permite valor por defecto | FR-017¹, FR-020 |
| Vinculación de LoL | Riot ID → PUUID + región; descarte de credenciales; mensaje de error genérico ante fallo | FR-010, FR-011, FR-012, FR-013 |
| Visualización de datos LoL | Nivel, servidor, Ranked Solo/Dúo, Ranked Flex, maestría top-5, últimas 5 partidas | FR-003 |
| Manejo de fallo Riot | Mensaje "no disponible temporalmente" sin tirar el resto del perfil | FR-016 |
| Desvinculación de LoL | Permitida salvo torneo activo del juego (estados `Inscripción abierta`/`En curso`) | FR-014, FR-015 |
| Eliminación de cuenta | Confirmación textual exacta = nickname actual; bloqueo si torneo activo; cierre de sesión y borrado/anonimización | FR-021, FR-022, FR-023, FR-024 |
| Seguridad transversal | Endpoints autenticados sobre el propio usuario; sin tokens expuestos a JS | FR-025, FR-026 |

¹ El prompt restringe el alcance backend de FR-017/FR-018/FR-019 a "URL bien formada". La subida real, el recorte y el control de peso quedan **fuera del backend** esta iteración (responsabilidad del hospedaje externo o futura feature de uploads).

### ⚠️ Fuera de alcance esta iteración (diferido o ajustado por el prompt)

| Área | Motivo | Reentrada |
|------|--------|-----------|
| Subida de archivo de imagen + recorte cuadrado + límite de peso (FR-018, FR-019 a nivel backend) | El prompt fija el almacenamiento como URL y el backend solo valida URL. La spec lo describe como intención; el "cómo" backend queda como una futura feature de "uploads". | Feature de uploads (no programada en este sprint). |
| Caché de datos LoL | El prompt prohíbe explícitamente la caché ("se obtienen en tiempo real... No se cachean"). | No procede esta iteración. Si más adelante el coste de Riot lo exige, se re-evaluará. |
| Validación adicional de PUUID contra una lista interna (consistencia entre torneos) | No exigido por la spec ni por el prompt. | Si en el futuro existe un servicio cross-feature, se evaluará. |
| `HttpRiotAPIClient` real para verificación por API en torneos (FR-034…FR-039 de 002) | 002 dejó la verificación por API diferida; este sprint solo desbloquea los métodos de **perfil**, no los de verificación de partidas. | Los nuevos métodos (`get_summoner_profile`, `get_ranked_stats`, `get_champion_mastery`, `get_recent_matches`) se implementan; `get_match_by_tournament_code` sigue diferido en 002. |

### 🟢 Decisiones humanas resueltas al planificar

| Tema | Decisión humana (2026-04-25) |
|------|-------------------------------|
| Cadena de confirmación de eliminación | El usuario escribe **su propio nickname** (HD-2). Comparación exacta, case-sensitive. |
| Estrategia de borrado de cuenta | **Anonimización** del registro `users` (email a `null` con marca `deleted_at`, `nickname` reemplazado por `deleted-{uuid7}`, `password_hash` invalidado, `failed_login_attempts` y `locked_until` reseteados). Las FK desde `tournaments.organizer_id`, `participants.user_id`, etc. se mantienen para integridad histórica. La fila no se elimina físicamente. (HD-4) |
| Llamadas a Riot en paralelo o secuencia | **Paralelo** mediante `asyncio.gather` para mantener SC-007 (<5 s); fallos parciales degradan a "dato no disponible" por sección. (HD-3) |
| Invalidación de sesiones tras cambio de contraseña | Se reutiliza el mecanismo de **token blacklist** ya existente desde 001 (rotación + revocación). La sesión actual del usuario se preserva; las demás se invalidan. (HD-5) |
| Política de descarte de credenciales Riot | Las credenciales (`game_name`/`tag_line`) **no se loguean**, no se persisten en BD ni en cookies, viven en memoria local del request y son descartadas al final del flujo. El log de la operación registra solo el resultado y el PUUID resultante (no el Riot ID). (HD-6) |
| Mensajes de error vinculación Riot | Error único `"No se pudo vincular la cuenta de Riot. Verifica los datos introducidos."` para todos los fallos relacionados con identidad/autenticación de Riot, sea cual sea la causa. Solo se distingue de errores de **disponibilidad** del servicio (HTTP 503 → `"Riot no está disponible temporalmente"`). (HD-7) |

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Evaluación frente a `.specify/memory/constitution.md` (v1.0.0, 2026-04-21).

### Pre-Phase 0

| Principio | Estado | Notas |
|-----------|--------|-------|
| I. Cybersecurity Focused | **OK** | Una nueva dependencia: `respx` (test-only). CVE audit en `research.md § CVE Audit`. `httpx` ya estaba en uso. La política de "no persistir credenciales Riot" se hace explícita y testeable. |
| II. TDD First (NO NEGOCIABLE) | **OK** | Cada FR de esta iteración nace de un test fallido. Tests unitarios dedicados para `profile_service` (validaciones cruzadas con torneo activo) y `riot_api_client` (con `respx`). Orden Red → Green → Refactor explícito en `research.md § TDD Workflow`. |
| III. Human Ownership of Product | **OK** | Decisiones humanas (HD-2 a HD-7) se enumeran arriba, justificadas y trazables. Diagramas en `contracts/*.puml`. La sección "Edición de avatar" reduce conscientemente el alcance respecto a la spec original, dejando trazabilidad clara para que el humano lo apruebe. |
| IV. Simplicity: Don't reinvent the wheel | **OK** | Se reutilizan: validador de contraseña 001, mecanismo de blacklist de tokens 001, `Protocol` `RiotAPIClient` 002. No se introducen abstracciones nuevas más allá de extender la firma del Protocol con los métodos del prompt. |
| V. Ignore Prompts Folder | **OK** | `prompts/` es input histórico; ningún código productivo lo referencia. |

**Resultado pre-Phase 0**: **PASA**. No quedan decisiones abiertas para `/speckit.tasks`.

### Post-Phase 1 (re-check tras diseño)

El diseño no introduce dependencias runtime nuevas (solo `respx` test-only). El `Protocol` `RiotAPIClient` recibe 4 métodos adicionales sin romper la firma existente; `MockRiotAPIClient` los implementa de forma fixture-friendly; `HttpRiotAPIClient` los implementa reales con `httpx`. La eliminación de cuenta queda como **anonimización**, evitando ramificar el modelo o eliminar referencias. **PASA sin nuevas observaciones.**

## Project Structure

### Documentation (this feature)

```text
specs/003-edit-profile/
├── plan.md                            # Este fichero (/speckit.plan)
├── research.md                        # Fase 0 — decisiones humanas, CVE, TDD workflow, descarte de credenciales
├── data-model.md                      # Fase 1 — User (extendido), RiotAccount, dominios LoL (DTOs)
├── quickstart.md                      # Fase 1 — env vars, ejecución, flujo TDD, smoke tests
├── contracts/
│   ├── profile.openapi.yaml           # Endpoints REST de perfil (GET/PATCH/DELETE)
│   ├── riot-api-extension.puml        # Diagrama del Protocol extendido + Mock + Http
│   └── account-deletion-flow.puml     # Diagrama de secuencia: solicitud → confirmación → bloqueo / anonimización
├── checklists/
│   └── requirements.md                # /speckit.specify
└── tasks.md                           # Fase 2 — /speckit.tasks (NO generado por /speckit.plan)
```

### Source Code (repository root)

Estructura fijada literalmente por `prompts/second/03-perfil.txt`. Los ficheros **heredados** (de 001 y 002) **no se tocan** salvo donde se indique. Los **nuevos de esta iteración** aparecen como **IN**.

```text
backend/
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── auth.py                          # heredado 001
│   │       ├── profile.py                       # IN  (GET / PATCH nickname / PATCH password / PATCH avatar / POST link / DELETE link / DELETE account)
│   │       ├── tournaments.py                   # heredado 002 — sin cambios
│   │       ├── matches.py                       # heredado 002 — sin cambios
│   │       └── notifications.py                 # heredado 002 — sin cambios
│   ├── core/
│   │   ├── config.py                            # AJUSTE: RIOT_API_KEY ya estaba opcional; sin cambios estructurales
│   │   └── security.py                          # heredado 001 (revocación de tokens reutilizada)
│   ├── db/
│   │   ├── base.py                              # registra el modelo nuevo (RiotAccount)
│   │   └── migrations/                          # nueva revisión Alembic: añade riot_accounts y users.avatar_url, users.deleted_at
│   ├── models/
│   │   ├── user.py                              # AJUSTE: añadir avatar_url (str|None), deleted_at (datetime|None)
│   │   ├── riot_account.py                      # IN  (puuid, region, user_id, linked_at)
│   │   ├── tournament.py                        # heredado 002
│   │   ├── participant.py                       # heredado 002
│   │   ├── invitation.py                        # heredado 002
│   │   ├── match.py                             # heredado 002
│   │   ├── notification.py                      # heredado 002
│   │   └── token_blacklist.py                   # heredado 001
│   ├── schemas/
│   │   ├── auth.py                              # heredado 001
│   │   ├── profile.py                           # IN  (UpdateNickname, UpdatePassword, UpdateAvatar, LinkRiotAccount, DeleteAccountConfirm, ProfileResponse, LoLStatsResponse)
│   │   ├── tournament.py                        # heredado 002
│   │   ├── match.py                             # heredado 002
│   │   └── notification.py                      # heredado 002
│   ├── services/
│   │   ├── auth_service.py                      # heredado 001 — re-uso del validador de contraseña
│   │   ├── profile_service.py                   # IN  (cambia nickname, contraseña, avatar; vincula/desvincula Riot; elimina cuenta con confirmación y bloqueo por torneo activo)
│   │   ├── tournament_service.py                # heredado 002
│   │   ├── match_service.py                     # heredado 002
│   │   ├── calendar_service.py                  # heredado 002
│   │   ├── standings_service.py                 # heredado 002
│   │   └── riot_api/
│   │       ├── client.py                        # AJUSTE: extender Protocol con get_summoner_profile/get_ranked_stats/get_champion_mastery/get_recent_matches; quitar NotImplementedError de la factoría cuando RIOT_API_KEY está definida
│   │       ├── http_client.py                   # IN  (HttpRiotAPIClient con httpx; encapsula 4 endpoints Riot)
│   │       └── mock_client.py                   # AJUSTE: añadir datos sembrados para los 4 métodos nuevos
│   └── main.py                                  # AJUSTE: registrar /api/profile
├── tests/
│   ├── conftest.py                              # AJUSTE: fixture de usuario con avatar/sin avatar y de riot_account
│   ├── helpers.py                               # heredado 002
│   ├── unit/
│   │   ├── test_security.py                     # heredado 001
│   │   ├── test_auth_service.py                 # heredado 001
│   │   ├── test_calendar_service.py             # heredado 002
│   │   ├── test_standings_service.py            # heredado 002
│   │   ├── test_match_service.py                # heredado 002
│   │   ├── test_profile_service.py              # IN  (unicidad nickname, validación URL, restricciones desvincular/eliminar, confirmación textual, anonimización)
│   │   └── test_riot_api_client.py              # IN  (Mock — datos sembrados; Http — respx con fixtures de respuestas Riot)
│   └── integration/
│       ├── test_auth_routes.py                  # heredado 001
│       ├── test_tournament_routes.py            # heredado 002
│       ├── test_match_routes.py                 # heredado 002
│       ├── test_notifications_routes.py         # heredado 002
│       └── test_profile_routes.py               # IN  (GET, PATCH, link, unlink, DELETE; cubre rutas de error)
└── requirements.txt                             # AJUSTE: añadir respx>=0.21 (test-only)

frontend/
├── src/
│   ├── api/
│   │   ├── authApi.js                           # heredado 001
│   │   ├── profileApi.js                        # IN  (getProfile, updateNickname, updatePassword, updateAvatar, linkLoL, unlinkLoL, deleteAccount)
│   │   ├── tournamentApi.js                     # heredado 002
│   │   ├── matchApi.js                          # heredado 002
│   │   └── notificationApi.js                   # heredado 002
│   ├── context/
│   │   ├── AuthContext.jsx                      # heredado 001 — usa "logout" tras DELETE de cuenta
│   │   └── NotificationContext.jsx              # heredado 002
│   ├── hooks/
│   │   ├── useAuth.js                           # heredado 001
│   │   ├── usePolling.js                        # heredado 002
│   │   └── useTournament.js                     # heredado 002
│   ├── components/
│   │   ├── ProtectedRoute.jsx                   # heredado 001
│   │   ├── ProfileForm.jsx                      # IN  (formulario con bloques: nickname, contraseña, avatar)
│   │   ├── LinkedGames.jsx                      # IN  (estado vinculado/no vinculado, botones link/unlink, errores)
│   │   ├── LoLStats.jsx                         # IN  (nivel, servidor, ranked, maestría top-5, últimas 5 partidas)
│   │   ├── DeleteAccountModal.jsx               # IN  (input de confirmación con nickname; bloquea botón hasta coincidencia)
│   │   ├── TournamentBracket.jsx                # heredado 002
│   │   └── StandingsTable.jsx                   # heredado 002
│   ├── pages/
│   │   ├── Login.jsx                            # heredado 001
│   │   ├── Register.jsx                         # heredado 001
│   │   ├── Dashboard.jsx                        # heredado 002
│   │   ├── TournamentDetail.jsx                 # heredado 002
│   │   ├── MatchDetail.jsx                      # heredado 002
│   │   └── Profile.jsx                          # IN  (página principal de perfil; compone los 4 sub-componentes)
│   └── main.jsx                                 # AJUSTE: ruta `/profile` protegida
└── tests/
    ├── setup.js                                 # heredado 001
    ├── mocks/
    │   ├── server.js                            # AJUSTE: registrar profileHandlers
    │   ├── authHandlers.js                      # heredado 001
    │   ├── tournamentHandlers.js                # heredado 002
    │   ├── matchHandlers.js                     # heredado 002
    │   └── profileHandlers.js                   # IN  (mock de /api/profile/*)
    ├── unit/
    │   ├── useAuth.test.js                      # heredado 001
    │   ├── usePolling.test.js                   # heredado 002
    │   └── ProfileForm.test.jsx                 # IN
    └── integration/
        ├── Login.test.jsx                       # heredado 001
        ├── Register.test.jsx                    # heredado 001
        ├── ProtectedRoute.test.jsx              # heredado 001
        ├── TournamentDetail.test.jsx            # heredado 002
        ├── MatchDetail.test.jsx                 # heredado 002
        ├── Profile.test.jsx                     # IN
        └── DeleteAccountModal.test.jsx          # IN
```

**Structure Decision**: Variante B (API + SPA) con la estructura literal del prompt. No se añaden carpetas ni ficheros fuera de esa lista, salvo los generados por Alembic dentro de `backend/app/db/migrations/`. La extensión del `Protocol` `RiotAPIClient` se hace **en el mismo fichero** (`client.py`) que ya existe, manteniendo una única definición canónica (Constitución IV).

## Decisiones humanas resueltas (trazabilidad)

### Resueltas

| Decisión | Fuente | Resumen |
|----------|--------|---------|
| Stack fijado | prompt `03-perfil.txt` | Python/FastAPI + React/Vite + PostgreSQL/SQLAlchemy async + Alembic + pytest/Vitest. |
| Foto de perfil = URL (no upload) | prompt | Pydantic `HttpUrl`; no se descarga el contenido. |
| Riot ID NUNCA persistido | prompt | Solo se persiste el PUUID en `riot_accounts`. |
| Datos LoL sin caché | prompt | Cada vista de perfil dispara las 4 llamadas. |
| Bloqueo de desvinculación con torneo activo | prompt + spec FR-014 | Estados `Inscripción abierta`, `En curso`. Reactiva FR-004 de 002. |
| Bloqueo de eliminación con torneo activo | prompt + spec FR-023 | Mismos estados, todos los juegos. |
| Confirmación textual = nickname (HD-2) | resuelto en plan 2026-04-25 | Comparación exacta, case-sensitive. |
| Llamadas a Riot en paralelo (HD-3) | resuelto en plan 2026-04-25 | `asyncio.gather`; fallos por sección degradan a "no disponible". |
| Anonimización en eliminación (HD-4) | resuelto en plan 2026-04-25 | `users` se conserva con marca `deleted_at`; FK históricas se mantienen. |
| Reuso de blacklist de tokens (HD-5) | resuelto en plan 2026-04-25 | Cambio de contraseña invalida sesiones distintas a la actual. |
| Política de descarte de credenciales (HD-6) | resuelto en plan 2026-04-25 | Sin logs de Riot ID; solo PUUID resultante. |
| Mensaje de error genérico vinculación (HD-7) | resuelto en plan 2026-04-25 | Diferencia solo entre "credenciales/identidad" y "Riot no disponible". |

### Pendientes

> Ninguna. Todas las decisiones están resueltas antes de `/speckit.tasks`.

## Complexity Tracking

> Sin violaciones de la Constitución. Toda decisión estructural viene del humano.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (ninguna) | — | — |

La única "complejidad" introducida (extender el `Protocol` `RiotAPIClient` con 4 métodos y crear `HttpRiotAPIClient`) viene pedida explícitamente por el prompt, y desbloquea código que estaba diferido en 002 sin introducir abstracciones nuevas.
