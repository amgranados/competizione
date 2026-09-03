# Implementation Plan: Creación y gestión de torneos con calendario automático

**Branch**: `002-tournament-management` | **Date**: 2026-04-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-tournament-management/spec.md`
**Stack input (human)**: `prompts/second/02-torneo.txt` — el humano fija stack, librerías, estructura de carpetas, algoritmos y restricciones técnicas. Este plan lo asume sin cuestionarlo (Constitución IV). La carpeta `prompts/` es **input histórico**, no referenciado en runtime (Constitución V).

## Summary

Torneos 1v1 con calendario automático en formatos round-robin y eliminación directa. Backend Python/FastAPI expone endpoints REST; frontend React (Vite) consume la API y refresca vistas mediante **polling cada 10s** (sin WebSockets en esta fase). Los algoritmos de calendario son **implementación propia** (round-robin por rotación circular con jugador fantasma para N impar; eliminación directa con byes asignados a los participantes con inscripción más reciente). Los códigos de sala son UUIDv4 internos por enfrentamiento. La **vinculación de cuenta de Riot está fuera del alcance de esta iteración** (bloqueo declarado en la spec), por lo que la verificación por API (FR-034…FR-039) queda diferida; el **único mecanismo de registro de resultados** en esta iteración es el **override manual** (FR-040…FR-044). La interfaz `RiotAPIClient` y `MockRiotAPIClient` se preparan según el stack para la iteración futura, pero **no se cablean a ningún endpoint** ahora (Principio II: no hay código productivo sin un test que lo exija).

## Technical Context

**Language/Version**: Backend **Python ≥3.12**. Frontend **Node ≥20 (LTS)** para Vite.

**Primary Dependencies** (todas ya fijadas por el prompt del humano):
- Backend runtime: **FastAPI**, **SQLAlchemy 2.x async**, **Alembic**, **Pydantic v2**, **pydantic-settings**, **httpx** (preparado para futura integración Riot; no usado en runtime esta iteración), **PyJWT + passlib[bcrypt]** heredados de 001, `python-multipart>=0.0.9`, `slowapi` (herencia 001).
- Backend tests: **pytest**, **pytest-asyncio**, **httpx** (test client FastAPI), **pytest-cov**, **respx** (**nueva**; diferida: se instalará cuando la iteración futura introduzca tests de `HttpRiotAPIClient` — ver `research.md § Dependencias diferidas`).
- Frontend runtime: **React 18 + React Router v6** (heredados de 001), `fetch` nativo con `credentials: "include"` (sin axios, sin localStorage).
- Frontend tests: **Vitest**, `@testing-library/react`, `@testing-library/user-event`, **msw** (heredados de 001).
- **Sin librerías externas** para los algoritmos de calendario (prompt explícito).

**Storage**: **PostgreSQL 15+** vía SQLAlchemy async; migraciones con Alembic. Se añaden nuevas tablas (ver `data-model.md`); el esquema de 001 (`users`, `token_blacklist`) se conserva intacto.

**Testing**:
- **Principio II (NO NEGOCIABLE)**: todo código productivo nace de un test fallido (Red → Green → Refactor). Estructura TDD detallada en `research.md § TDD Workflow`.
- Tests unitarios específicos: `test_calendar_service.py` (rotación circular, byes), `test_standings_service.py` (orden, desempate directo, empate circular), `test_match_service.py` (validaciones de registro manual y avance de ronda).
- Tests de integración: `test_tournament_routes.py`, `test_match_routes.py`, `test_notifications_routes.py`.
- Tests frontend: `Login/Register` (herencia 001), `TournamentDetail`, `MatchDetail`, `ProtectedRoute`, `usePolling`.

**Target Platform**: Servidor Linux en producción; HTTPS obligatorio (cookies `Secure=True` de 001 lo exigen). Despliegue concreto a confirmar (no bloquea este plan).

**Project Type**: **Backend API + Frontend SPA separados** (mismo layout que 001). Estructura fijada literalmente por el prompt; ver "Project Structure".

**Performance Goals**: No especificado. Indicativo, alineado con SC-003: la clasificación o el cuadro reflejan cambios en **<5 s** para el usuario tras confirmarse un resultado; con polling cada 10 s esto implica p95 de latencia backend muy inferior (<2 s) en endpoints de lectura.

**Constraints**:
- **IDs en formato UUID v4** (restricción técnica del prompt).
- **Tournament codes únicos por enfrentamiento, UUID v4 interno** en esta iteración; se generan al iniciar el torneo (round-robin: todas las rondas; eliminación directa: sólo primera ronda, el resto al cerrarse la anterior).
- **Byes no generan código de sala ni puntúan en clasificación**.
- **Etiqueta "Introducido manualmente" permanente e inamovible** — persistida como valor en DB, inmutable por contrato (FR-042).
- **Riot API sólo se consulta a petición explícita del usuario** (sin verificación automática en background) — aplicable en la iteración futura; no cableado ahora.
- **Polling frontend**: `setInterval` cada **10 s** sobre endpoints de notificaciones, calendario y clasificación. No WebSockets/SSE en MVP.
- Heredados de 001: `SECRET_KEY ≥32` chars desde env, CORS restringido a `FRONTEND_ORIGIN`, cookies HttpOnly/Secure/SameSite=lax.
- **Nuevas variables de entorno** (ver `quickstart.md § Env vars`): `RIOT_API_KEY` (**opcional**; su ausencia fuerza `MockRiotAPIClient` con log explícito — prompt). En esta iteración, el cliente no se instancia salvo en tests, por lo que la var no afecta al comportamiento productivo.

**Scale/Scope**: Primera versión. Escala estimada para el MVP: hasta ~32 participantes por torneo, varios torneos activos en paralelo por organizador. No hay SLA fijado.

## Scope de la iteración actual

Derivado de las anotaciones ⚠️ en `spec.md`. **Reglas claras** para evitar ambigüedades:

### ✅ Implementado esta iteración

| Área | Funcionalidad | FR cubiertos |
|------|---------------|--------------|
| Torneos | Crear, listar, detalle, abrir inscripciones, iniciar, cancelar, finalizar auto | FR-005…FR-008, FR-016…FR-022, FR-055…FR-058 |
| Modificaciones pre-inicio | Nombre, fecha, formato, invitar, eliminar participantes, cancelar invitación | FR-021, FR-022 |
| Invitaciones | Crear, listar, aceptar, rechazar, cancelar, expiración a 48h (check-on-read) | FR-009, FR-011…FR-015 |
| Participantes | Confirmación al aceptar; baja pre-inicio | FR-015 |
| Calendario | Round-robin (rotación circular); eliminación directa (byes a más recientes); cierre de ronda → generación siguiente | FR-023…FR-030 |
| Códigos de sala | UUID v4 interno, único por enfrentamiento, con timestamp | FR-031…FR-033 |
| Resultado manual | Registro por organizador, etiqueta permanente, avance de ganador, sin disputa | FR-040…FR-044 |
| Restricciones | No registrar en rondas futuras; no avanzar sin confirmación | FR-045, FR-046 |
| Clasificación | Tabla round-robin ordenada por victorias → directo → empate circular por fecha inscripción → id (desempate estable) | FR-047, FR-048 |
| Avance eliminación | Automático al confirmar; gran final → torneo "Finalizado" | FR-049, FR-050 |
| Consulta | Próximos enfrentamientos, resultados pasados, tabla/cuadro | FR-051…FR-054 |
| Notificaciones in-app | Persistidas en BBDD; polling frontend cada 10s | Soporte transversal (US1 ac. 4, FR-011, FR-057) |

### ⚠️ Fuera de alcance esta iteración (diferido)

| Área | Motivo | Reentrada |
|------|--------|-----------|
| Vinculación de cuenta de Riot (crear, desvincular, sustituir) | Bloqueado por la spec (nota al inicio) | Feature posterior; entidad `RiotAccount` **no se crea ahora** |
| Restricción FR-010 (invitado debe tener cuenta LoL vinculada) | Depende del bloque anterior | Reentrada junto con la vinculación |
| FR-004 (bloqueo de desvinculación si participante activo) | Depende de la vinculación | Reentrada junto con la vinculación |
| Verificación por API (FR-034…FR-039) | Depende de integración Riot | Endpoint **no expuesto** esta iteración; manual override cubre la disputa (FR-040) |
| `HttpRiotAPIClient` (implementación real del Protocol) | TDD: ningún test lo requiere aún | Se implementará cuando se escriban sus tests |
| SC-002 y parte API de SC-004 | Dependen de la verificación por API | Reentrada con la verificación |

### 🟢 Decisiones humanas transversales resueltas al planificar

| Tema | Decisión humana (2026-04-24) |
|------|-------------------------------|
| Sistema de amistades (check en invitaciones) | Se permite invitar a **cualquier usuario registrado** en esta iteración. El check de amistad entrará cuando exista el servicio de amistades (filtro adicional en `tournament_service.invite()`, sin impacto estructural). Ver `research.md § HD-1`. |

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Evaluación frente a `.specify/memory/constitution.md` (v1.0.0, 2026-04-21).

### Pre-Phase 0

| Principio | Estado | Notas |
|-----------|--------|-------|
| I. Cybersecurity Focused | **OK** | No se introducen dependencias runtime nuevas. `respx` (test-only) queda diferida; su CVE audit se hará cuando se instale. Ver `research.md § CVE Audit`. |
| II. TDD First (NO NEGOCIABLE) | **OK** | Cada FR implementada nace de un test fallido. Orden Red → Green → Refactor explícito en `research.md § TDD Workflow`. Tests unitarios dedicados para los algoritmos de calendario y clasificación (donde la complejidad lógica es alta). |
| III. Human Ownership of Product | **OK** | El scope fue marcado por el humano en `spec.md`. La decisión sobre el sistema de amistades (HD-1) quedó resuelta por el humano el 2026-04-24: opción B — invitar a cualquier usuario registrado esta iteración. Ver `research.md § HD-1`. Diagramas en `contracts/*.puml`. |
| IV. Simplicity: Don't reinvent the wheel | **OK** | Stack y estructura de carpetas literalmente respetados. No se reemplazan librerías ni se añaden abstracciones propias más allá de las pedidas (`RiotAPIClient` Protocol, `MockRiotAPIClient`). |
| V. Ignore Prompts Folder | **OK** | `prompts/` se trata como input histórico; no se añade código, dependencias ni rutas que lo referencien en tiempo de ejecución. |

**Resultado pre-Phase 0**: **PASA**. La única pregunta pendiente (sistema de amistades) fue resuelta por el humano el 2026-04-24 (opción B); no quedan decisiones abiertas para `/speckit.tasks`.

### Post-Phase 1 (re-check tras diseño)

El diseño (entidades, contratos, algoritmos) no introduce abstracciones no pedidas ni dependencias nuevas. El uso de una enumeración para el estado de `Match` (`pending` | `manual`) y la reserva del valor `verified_api` como constante **no persistida aún** preserva la forma del dominio para la iteración futura sin adelantar código no testeado. **PASA sin nuevas observaciones**.

## Project Structure

### Documentation (this feature)

```text
specs/002-tournament-management/
├── plan.md                           # Este fichero (/speckit.plan)
├── research.md                       # Fase 0 — decisiones, algoritmos, CVE
├── data-model.md                     # Fase 1 — Tournament, Participant, Invitation, Match, Notification, Round (derivado)
├── quickstart.md                     # Fase 1 — puesta en marcha + flujo TDD + env vars
├── contracts/
│   ├── tournaments.openapi.yaml      # Endpoints torneos/invitaciones/participantes
│   ├── matches.openapi.yaml          # Endpoints de enfrentamientos y resultado manual
│   ├── notifications.openapi.yaml    # Endpoints de notificaciones + polling
│   ├── tournament-lifecycle.puml     # Diagrama de estados de torneo
│   ├── match-lifecycle.puml          # Diagrama de estados de enfrentamiento (incluye placeholder verified_api)
│   └── round-robin-rotation.puml    # Diagrama del algoritmo de rotación circular
├── checklists/
│   └── requirements.md               # /speckit.specify
└── tasks.md                          # Fase 2 — /speckit.tasks (NO generado por /speckit.plan)
```

### Source Code (repository root)

Estructura fijada literalmente por `prompts/second/02-torneo.txt` (añadido sobre el módulo de autenticación existente de 001). Los ficheros **en gris** son heredados de 001 y no se tocan. Los **nuevos de esta iteración** aparecen como **IN**; los **diferidos** aparecen como **DEFER**.

```text
backend/
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── auth.py                         # heredado 001
│   │       ├── tournaments.py                  # IN  (torneos, invitaciones, participantes)
│   │       ├── matches.py                      # IN  (detalle, resultado manual)
│   │       └── notifications.py                # IN  (listado, marcar leída)
│   ├── core/
│   │   ├── config.py                           # ampliado: añade RIOT_API_KEY opcional
│   │   └── security.py                         # heredado 001
│   ├── db/
│   │   ├── base.py                             # registra nuevos modelos
│   │   └── migrations/                         # nueva revisión Alembic para las tablas 002
│   ├── models/
│   │   ├── user.py                             # heredado 001
│   │   ├── token_blacklist.py                  # heredado 001
│   │   ├── riot_account.py                     # DEFER (no se crea esta iteración)
│   │   ├── tournament.py                       # IN
│   │   ├── participant.py                      # IN
│   │   ├── invitation.py                       # IN
│   │   ├── match.py                            # IN
│   │   └── notification.py                     # IN
│   ├── schemas/
│   │   ├── auth.py                             # heredado 001
│   │   ├── tournament.py                       # IN
│   │   ├── match.py                            # IN
│   │   └── notification.py                     # IN
│   ├── services/
│   │   ├── auth_service.py                     # heredado 001
│   │   ├── tournament_service.py               # IN  (crear, abrir, iniciar, cancelar, modificar)
│   │   ├── match_service.py                    # IN  (resultado manual, avance de ganador, finalización auto)
│   │   ├── calendar_service.py                 # IN  (round-robin + eliminación directa)
│   │   ├── standings_service.py                # IN  (clasificación + desempates)
│   │   └── riot_api/
│   │       ├── client.py                       # IN  (Protocol RiotAPIClient + factory por env)
│   │       ├── http_client.py                  # DEFER (no tiene test aún)
│   │       └── mock_client.py                  # IN  (fixture-friendly, usado en tests de 002 vacíos aún; preparado para iteración futura)
│   └── main.py                                 # actualizado: registrar nuevas rutas
├── tests/
│   ├── conftest.py                             # actualizado: fixture de torneo/participantes/match
│   ├── unit/
│   │   ├── test_security.py                    # heredado 001
│   │   ├── test_auth_service.py                # heredado 001
│   │   ├── test_calendar_service.py            # IN
│   │   ├── test_standings_service.py           # IN
│   │   └── test_match_service.py               # IN  (sólo rama manual + avance; rama API diferida)
│   └── integration/
│       ├── test_auth_routes.py                 # heredado 001
│       ├── test_tournament_routes.py           # IN
│       ├── test_match_routes.py                # IN  (sin verify endpoint)
│       └── test_notifications_routes.py        # IN
└── requirements.txt                            # SIN CAMBIOS esta iteración (respx diferida)

frontend/
├── src/
│   ├── api/
│   │   ├── authApi.js                          # heredado 001
│   │   ├── tournamentApi.js                    # IN
│   │   ├── matchApi.js                         # IN
│   │   └── notificationApi.js                  # IN
│   ├── context/
│   │   ├── AuthContext.jsx                     # heredado 001
│   │   └── NotificationContext.jsx             # IN  (polling 10s)
│   ├── hooks/
│   │   ├── useAuth.js                          # heredado 001
│   │   ├── useTournament.js                    # IN
│   │   └── usePolling.js                       # IN  (genérico, reutilizable)
│   ├── components/
│   │   ├── ProtectedRoute.jsx                  # heredado 001
│   │   ├── TournamentBracket.jsx               # IN
│   │   └── StandingsTable.jsx                  # IN
│   ├── pages/
│   │   ├── Login.jsx                           # heredado 001
│   │   ├── Register.jsx                        # heredado 001
│   │   ├── Dashboard.jsx                       # IN  (listado de torneos propios/invitaciones)
│   │   ├── TournamentDetail.jsx                # IN
│   │   └── MatchDetail.jsx                     # IN
│   └── main.jsx                                # actualizado: rutas de torneo/match
└── tests/
    ├── setup.js                                # heredado 001
    ├── mocks/
    │   ├── authHandlers.js                     # heredado 001
    │   ├── tournamentHandlers.js               # IN
    │   └── matchHandlers.js                    # IN
    ├── unit/
    │   ├── useAuth.test.js                     # heredado 001
    │   └── usePolling.test.js                  # IN
    └── integration/
        ├── Login.test.jsx                      # heredado 001
        ├── Register.test.jsx                   # heredado 001
        ├── ProtectedRoute.test.jsx             # heredado 001
        ├── TournamentDetail.test.jsx           # IN
        └── MatchDetail.test.jsx                # IN
```

**Structure Decision**: Variante B (API + SPA) con la estructura literal impuesta por el humano. Los ficheros marcados **DEFER** se nombran en la estructura de carpetas porque así los fijó el humano, pero **no se crearán en esta iteración**; entrarán junto con los tests que los justifiquen (Principio II). No se añaden carpetas ni ficheros fuera de esa lista salvo los generados por Alembic dentro de `backend/app/db/migrations/`.

## Decisiones humanas resueltas (trazabilidad)

Siguiendo el patrón de 001-user-auth, se listan las decisiones tomadas (por el humano en la spec o en el prompt de stack) y las que quedan pendientes:

### Resueltas

| Decisión | Fuente | Resumen |
|----------|--------|---------|
| Stack fijado | prompt `02-torneo.txt` | Python/FastAPI + React/Vite + PostgreSQL/SQLAlchemy async + Alembic + pytest/Vitest. Sin cuestionarlo. |
| Algoritmos de calendario propios | prompt | Round-robin por rotación circular con jugador fantasma; eliminación directa con byes a participantes de inscripción más reciente. Sin librerías externas. |
| Polling 10 s, no WebSocket | prompt | `setInterval` en frontend sobre notificaciones/calendario/clasificación. |
| IDs UUID v4 | prompt | En todas las entidades nuevas. |
| Tournament code único por enfrentamiento | prompt | Generado al iniciar torneo (round-robin: todo; eliminación: sólo primera ronda) o al cerrar ronda. |
| Etiqueta manual inamovible | prompt + spec FR-042 | Aun con API verificable posterior, se mantiene "manual". |
| Byes sin código ni puntos | prompt + spec FR-048 | Formalizado en `data-model.md`. |
| `RiotAPIClient` Protocol + Mock por defecto si falta `RIOT_API_KEY` con log | prompt | Implementado como Protocol; `MockRiotAPIClient` preparado; `HttpRiotAPIClient` DEFER. |
| Vinculación de cuenta Riot out-of-scope | spec (nota inicial y marcadores ⚠️) | Ver tabla § Fuera de alcance. |

### Pendientes

> Ninguna. Todas las decisiones están resueltas antes de `/speckit.tasks`.

## Complexity Tracking

> Sin violaciones de la Constitución. Todas las decisiones estructurales vienen impuestas por el humano.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (ninguna) | — | — |

La única "complejidad" introducida (Protocol `RiotAPIClient` + Mock sin endpoint que lo use aún) viene pedida explícitamente por el humano en el prompt de stack.
