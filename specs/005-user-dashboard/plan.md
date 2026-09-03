# Implementation Plan: Dashboard

**Branch**: `005-user-dashboard` | **Date**: 2026-06-08 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-user-dashboard/spec.md`

## Summary

Dashboard global post-login: saludo personalizado, **4 tarjetas** de estadísticas
(Torneos activos con variación semanal, Victorias totales + winrate, Mejor streak con
torneo, **Nº de amigos**), sección "Mis torneos" (torneos `in_progress` u `open` del
usuario) y un feed de **actividad reciente** del usuario y sus amigos.

Enfoque técnico (dictado por el prompt, ver Constitution Check):
- **Backend FastAPI**: un único endpoint `GET /api/dashboard` devuelve `DashboardResponse`.
  Un `dashboard_service` orquesta tres servicios: `stats_service` (métricas calculadas en
  caliente, sin caché), `activity_service` (lectura del feed) y reutiliza
  `tournament_service`/consultas para "Mis torneos".
- **Tabla nueva `activity_feed`** (`id, actor_id, event_type, tournament_id, created_at`):
  los eventos se **escriben en el momento de la acción** (victoria, unión, invitación,
  creación de torneo) desde los servicios existentes vía `activity_service.record(...)`.
  Esto **anula** la asunción de la spec (línea 160) de derivar el feed de tablas existentes:
  el prompt es la dirección técnica autoritativa (Constitution IV).
- **Frontend React (Vite)**: se **reescribe** la `Dashboard.jsx` existente (hoy es un hub
  de creación de torneos) para consumir `GET /api/dashboard` y renderizar las nuevas
  secciones con componentes reutilizables `StatsCard`, `TournamentCard`, `ActivityFeed`.

## Technical Context

**Language/Version**: Backend Python ≥3.12 · Frontend Node ≥20 (LTS) para Vite
**Primary Dependencies**: FastAPI · SQLAlchemy async · Alembic · Pydantic v2 ·
pydantic-settings · React + React Router v6 (`fetch` nativo con `credentials:"include"`)
**Storage**: PostgreSQL 15+ vía SQLAlchemy async; migración Alembic que **añade** la tabla
`activity_feed`. El esquema de 001–004 se conserva intacto. No se modifican tablas existentes.
**Testing**: Backend pytest + pytest-asyncio + httpx + pytest-cov ·
Frontend Vitest + @testing-library/react + @testing-library/user-event + msw
**Target Platform**: Servidor Linux (contenedor Docker) + cliente web autenticado
**Project Type**: Web application (backend FastAPI + frontend React), ya existente
**Performance Goals**: Dashboard completo < 2 s en condiciones normales (SC-001);
métricas calculadas en caliente en una sola petición.
**Constraints**: Sin tiempo real (FR-007, SC-010); feed sin paginación ni filtros;
todas las secciones en una sola petición a `GET /api/dashboard` (FR-024); auth obligatoria
y rechazo de peticiones en nombre de otro usuario (FR-023).
**Scale/Scope**: 1 endpoint backend, 3 servicios nuevos + 1 modelo + 1 migración;
1 página + 3 componentes frontend + 1 cliente api. Feed limitado a **6** eventos.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Estado | Justificación |
|-----------|--------|---------------|
| **I. Cybersecurity Focused** | ✅ PASS | No se añaden dependencias nuevas: todo el stack (FastAPI, SQLAlchemy, Alembic, Pydantic, React Router, Vitest, msw, httpx) ya está auditado y en uso en 001–004. Sección de auditoría CVE en `research.md` confirma "sin dependencias nuevas → sin nueva superficie". El endpoint reutiliza `get_current_user` (001) y filtra por `current_user.id` (FR-023). |
| **II. TDD First (NON-NEGOTIABLE)** | ✅ PASS | `tasks.md` (fase siguiente) ordenará test→código en cada unidad. Tests de contrato/integración/unidad enumerados en este plan y en `quickstart.md`. Se reusa el `Dashboard.test.jsx` existente, reescribiéndolo junto con la página. |
| **III. Human Ownership of Product** | ✅ PASS | Dos decisiones de producto abiertas se resolvieron **preguntando al humano** (4ª tarjeta = Nº de amigos; token "en curso" = `in_progress`). Decisiones técnicas documentadas con fuentes en `research.md`. Diagramas en PlantUML. |
| **IV. Simplicity: Don't reinvent the wheel** | ✅ PASS | Se usan exactamente las herramientas que el prompt especifica; no se introducen colas, caché ni Redis. La tabla `activity_feed` y la estructura de carpetas siguen el prompt al pie de la letra. La consulta de amigos reutiliza el patrón `_pair_filter` de `friends_service`. |
| **V. Ignore Prompts Folder** | ✅ PASS | El contenido de `prompts/` se usa solo como fuente de la especificación; no forma parte del producto entregable. |

**Resultado del gate: PASS (sin violaciones).** No se requiere Complexity Tracking.

### Hallazgos para supervisión humana (Principio I y III)

1. **Inconsistencia de estado "en curso"** (resuelta por el humano → `in_progress`):
   `tournament_service` nunca asigna `in_progress` (solo draft→open→finished/cancelled),
   pero `profile_service._ACTIVE_TOURNAMENT_STATES = ("open","in_progress")` y los tests
   ya usan `state="in_progress"`. El **frontend** usa el literal `'active'`. La tarea de
   implementación deberá **unificar** el frontend a `in_progress` o documentar el mapeo.
   Detalle y fuentes en `research.md §Decisión 2`.
2. **Contradicción spec ↔ prompt sobre el feed**: la spec asume derivar el feed de tablas
   existentes; el prompt exige una tabla `activity_feed` escrita en caliente. Se sigue el
   prompt (Constitution IV). Implicación: hay que **instrumentar** los servicios existentes
   (match, tournament, invitation) para emitir eventos — cambio aditivo, sin alterar su
   contrato. Ver `research.md §Decisión 3`.

## Project Structure

### Documentation (this feature)

```text
specs/005-user-dashboard/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── dashboard.openapi.yaml
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/routes/
│   │   └── dashboard.py            # GET /api/dashboard → DashboardResponse (auth)
│   ├── models/
│   │   └── activity_feed.py        # tabla activity_feed: id, actor_id, event_type,
│   │                               # tournament_id, created_at
│   ├── schemas/
│   │   └── dashboard.py            # StatsCards, TournamentCard, ActivityEvent,
│   │                               # DashboardResponse
│   ├── services/
│   │   ├── dashboard_service.py    # orquesta saludo + stats + mis torneos + feed
│   │   ├── stats_service.py        # torneos activos+variación, victorias, winrate, streak, nº amigos
│   │   └── activity_service.py     # record(...) (escritura) + list_recent(...) (lectura, ≤6)
│   ├── db/migrations/versions/
│   │   └── <rev>_add_activity_feed.py   # Alembic: CREATE TABLE activity_feed
│   └── main.py                     # incluir el router de dashboard
└── tests/
    ├── unit/
    │   ├── test_stats_service.py       # variación semanal, winrate, streak por torneo, exclusión byes, nº amigos
    │   └── test_activity_service.py    # límite 6, exclusión no-amigos, orden cronológico, resiliencia
    └── integration/
        └── test_dashboard_routes.py    # GET /api/dashboard: 200 con datos, 401 sin auth, aislamiento por usuario

frontend/
├── src/
│   ├── api/
│   │   └── dashboardApi.js         # getDashboard()
│   ├── pages/
│   │   └── Dashboard.jsx           # REESCRITA: saludo + 4 StatsCard + Mis torneos + ActivityFeed
│   └── components/
│       ├── StatsCard.jsx           # tarjeta de métrica con variación (+/-/0)
│       ├── TournamentCard.jsx      # tarjeta de torneo activo/próximo (estado, formato, jugadores, ronda/fecha)
│       └── ActivityFeed.jsx        # feed cronológico con enlaces a usuarios y torneos
└── tests/
    ├── mocks/
    │   └── dashboardHandlers.js    # msw handler para GET /api/dashboard
    ├── unit/
    │   ├── StatsCard.test.jsx      # variación positiva, negativa y cero
    │   └── ActivityFeed.test.jsx   # render de cada tipo de evento + entrada resiliente
    └── integration/
        └── Dashboard.test.jsx      # REESCRITA: saludo, 4 tarjetas, mis torneos, feed, estados vacíos
```

**Structure Decision**: Web application existente (Opción 2). Se reutilizan los módulos
ya presentes en `backend/app/{api/routes,models,schemas,services,db}` y
`frontend/src/{api,pages,components}`. Esta feature **añade** archivos nuevos y **reescribe**
dos existentes (`frontend/src/pages/Dashboard.jsx` y su test de integración), porque la
`Dashboard.jsx` actual es un hub de creación de torneos que no cumple la nueva spec. La
funcionalidad de creación/invitaciones que hoy vive en `Dashboard.jsx` permanece accesible
desde la sección de Torneos (fuera del alcance de esta feature, ver Assumptions de la spec).

## Complexity Tracking

> No aplica: el Constitution Check pasa sin violaciones.
