# Phase 1 — Quickstart & Test Plan: Dashboard (005)

Cómo arrancar, y el mapa **TDD (Red→Green→Refactor, Constitution II)** de tests a requisitos.
Cada test se escribe **antes** que el código que lo hace pasar.

---

## Arrancar en local

Variables de entorno backend requeridas (ya usadas en 001–004; el prompt las repite):
`DATABASE_URL`, `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES=15`,
`REFRESH_TOKEN_EXPIRE_DAYS=7`, `FRONTEND_ORIGIN`. (Ver `.env.example`.)

```bash
# Backend
cd backend
alembic upgrade head            # aplica la migración de activity_feed
pytest                          # toda la suite
pytest tests/unit/test_stats_service.py tests/unit/test_activity_service.py
pytest tests/integration/test_dashboard_routes.py
ruff check .

# Frontend
cd frontend
npm test                        # Vitest
npm run dev                     # Vite dev server
```

Comando del repo (CLAUDE.md): `cd src; pytest; ruff check .` — aquí el backend vive en
`backend/`, por lo que se usa `cd backend`.

---

## Humo manual (smoke) — verifica las 3 User Stories

1. Autenticarse y navegar a `/dashboard` (página de aterrizaje post-login, FR-024).
2. **US1**: ver "Hola, <nickname>" + subtítulo fijo + 4 tarjetas (Torneos activos con
   variación, Victorias totales + winrate, Mejor streak + torneo, Nº de amigos).
3. **US2**: ver "Mis torneos" con tarjetas in_progress/open; pulsar "Ver todos" → navega a
   Torneos.
4. **US3**: ver feed (≤6) con eventos propios y de amigos, más reciente arriba; nombres de
   usuario y torneo clicables.
5. Usuario nuevo (sin datos): 4 tarjetas en neutro, "Mis torneos" y feed con estado vacío,
   **cero errores** (SC-008).

---

## Backend — tests (TDD)

### `tests/unit/test_stats_service.py`  (US1)
| Test | Requisito |
|------|-----------|
| Torneos activos cuenta solo `in_progress` donde el usuario participa | FR-003 |
| Variación semanal = activos_now − activos_hace_7d; **neutra/None sin histórico** | FR-004, edge case |
| Victorias totales excluyen byes (`is_bye=True` no cuenta) | FR-005 |
| Winrate = wins/(wins+losses)·100; **0 sin partidas, sin ZeroDivision** | FR-005, FR-008 |
| Mejor streak = máx. victorias consecutivas **por torneo** (orden `resolved_at`) | FR-006 |
| Streak devuelve `tournament_id`+`name` de la **última** victoria de la racha | FR-006, Assumption |
| Nº de amigos = `COUNT` friendships `accepted` (ambas direcciones), excluye `deleted_at` | FR-025 (4ª tarjeta) |
| Usuario sin datos → todo neutro, sin error | FR-008, SC-003 |

### `tests/unit/test_activity_service.py`  (US3)
| Test | Requisito |
|------|-----------|
| `record(...)` inserta una fila con actor/tipo/torneo/created_at | Decisión 3 |
| `list_recent` devuelve **máx. 6** eventos | límite 6 (prompt) |
| Orden cronológico desc (más reciente primero) | FR-020, SC-006 |
| Excluye eventos cuyo actor **no es amigo ni el propio usuario** | FR-019, SC-005 |
| Incluye eventos **propios** del usuario | FR-015, US3 escenario 6 |
| Amigo eliminado (`deleted_at`/sin `accepted`) → sus eventos no aparecen | edge case spec |
| Torneo borrado (`tournament_id` NULL) → entrada resiliente, sin romper | FR-022, US3 escenario 7 |

### `tests/integration/test_dashboard_routes.py`
| Test | Requisito |
|------|-----------|
| `GET /api/dashboard` sin auth → **401** | FR-023 |
| `GET /api/dashboard` autenticado → **200** con `DashboardResponse` completo | FR-024, contrato |
| El usuario A nunca ve datos/eventos de no-amigos (aislamiento) | FR-005/023, SC-005 |
| Usuario nuevo → 200 con stats neutras y arrays vacíos | SC-008 |
| `my_tournaments` excluye finished/cancelled y torneos ajenos | FR-010, SC-004 |

> **Instrumentación**: tests que verifican que `match_service`/`tournament_service` emiten el
> evento correcto (`MATCH_WIN`, `TOURNAMENT_JOIN`, `TOURNAMENT_INVITE`, `TOURNAMENT_CREATE`)
> al ocurrir la acción. Se escriben junto a los cambios aditivos en esos servicios.

---

## Frontend — tests (TDD)

### `tests/unit/StatsCard.test.jsx`  (US1)
- Renderiza variación **positiva** (`+1`), **negativa** (`-2`) y **cero/neutra** (sin signo).
- Winrate `0%` sin romper cuando no hay partidas.

### `tests/unit/ActivityFeed.test.jsx`  (US3)
- Renderiza cada tipo de evento (MATCH_WIN, TOURNAMENT_JOIN, TOURNAMENT_INVITE,
  TOURNAMENT_CREATE) con actor, acción, torneo y tiempo relativo.
- Entrada **resiliente**: actor/torneo inexistente → texto sin enlace, no se rompe (FR-022).
- Enlaces de actor y torneo apuntan a `/users/:nickname` y `/tournaments/:id` (FR-018).

### `tests/integration/Dashboard.test.jsx`  (REESCRITO)
> El test actual cubre el viejo hub de creación de torneos; se **reescribe** para la nueva
> spec (usar `tests/mocks/dashboardHandlers.js` con msw sobre `GET /api/dashboard`).

| Test | Requisito |
|------|-----------|
| Muestra "Hola, <nickname>" y el subtítulo fijo | FR-001/002, SC-002 |
| Muestra las 4 tarjetas con los valores del mock | FR-003..006, FR-025 |
| "Mis torneos" lista las tarjetas del mock; "Ver todos" navega a Torneos | FR-009/013, SC-009 |
| Feed muestra ≤6 eventos en orden, con enlaces | FR-015..020 |
| Estados vacíos (sin torneos / sin actividad) informativos, sin error | FR-014/021, SC-008 |

---

## Definición de hecho (gates)

- [X] Todos los tests anteriores **rojos primero**, luego verdes (Constitution II). — cada unidad
      se confirmó en Rojo antes de implementar (ver notas por tarea en `tasks.md`).
- [~] `ruff check .` limpio en backend. — `ruff` **no instalado** y no declarado en
      `requirements.txt`/`pyproject.toml`; no se instaló (Constitution I / T001). Sustituto:
      `py_compile` limpio + escaneo AST sin imports sin usar. **Pendiente humano**: añadir `ruff`
      al toolchain (con su revisión) si se quiere el gate real.
- [X] Migración `activity_feed` aplica y revierte (`alembic upgrade head` / `downgrade -1`). —
      verificado dos veces sobre SQLite (cadena 001→005 y reverso a `e2a4b5c7d9f1`).
- [X] `GET /api/dashboard` cumple el contrato `contracts/dashboard.openapi.yaml`. — validado por
      `tests/integration/test_dashboard_routes.py` (401 sin auth, DashboardResponse completo,
      usuario nuevo neutro, aislamiento).
- [X] **HALLAZGO de estado** (`research.md` Decisión 2) resuelto o documentado. — Opción 2
      (mapeo en read layer, sin tocar el dominio); ver `research.md §Decisión 2 → RESOLUCIÓN (T030)`.
      La unificación del dominio queda fuera de alcance y requiere aprobación humana.
- [X] **Sin dependencias nuevas**; si alguna fuera necesaria, parar y pedir análisis CVE
      (Constitution I). — no se añadió ninguna dependencia pip/npm.
