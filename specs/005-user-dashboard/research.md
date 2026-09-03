# Phase 0 — Research: Dashboard (005)

Resuelve los `NEEDS CLARIFICATION` de la spec y fija las decisiones técnicas con sus
fuentes (Constitution III: "Technical decisions must be explained in detail and list your
sources"). Todas las rutas de código citadas son del repo en `005-user-dashboard`.

---

## Decisión 1 — 4ª tarjeta de estadísticas (resuelve FR-025)

- **Decisión**: La 4ª tarjeta es **"Nº de amigos"**: total de amistades `accepted` del
  usuario autenticado.
- **Rationale**: El humano lo decidió explícitamente (Constitution III). El prompt describe
  solo 3 tarjetas, pero FR-025 quedó como `[NEEDS CLARIFICATION]` y la `Dashboard.jsx`
  actual ya renderiza una rejilla de 4 tarjetas (`gridTemplateColumns: "repeat(4, 1fr)"`,
  [Dashboard.jsx:115](../../frontend/src/pages/Dashboard.jsx#L115)). "Nº de amigos" reutiliza
  directamente la tabla `friendships` de 004 sin lógica nueva.
- **Cálculo**: `COUNT(*)` de `friendships` con `status='accepted'` donde el usuario es
  `requester_id` o `addressee_id`, excluyendo usuarios anonimizados (`deleted_at IS NULL`).
  Se reutiliza el patrón `_pair_filter` de
  [friends_service.py:77](../../backend/app/services/friends_service.py#L77).
- **Alternativas consideradas**: invitaciones pendientes (menos estable, fluctúa), partidas
  jugadas (redundante con winrate). Descartadas por el humano.

---

## Decisión 2 — Token canónico de "torneo en curso"

- **Decisión**: Usar **`in_progress`** como estado de "En curso"; "Inscripción abierta" es
  **`open`**. Para "Mis torneos" → `state IN ('in_progress','open')`. Para "Torneos activos"
  (tarjeta de stats) → `state = 'in_progress'` (solo en curso, no inscripción).
- **Rationale**: El humano eligió alinear con el **precedente backend**:
  - [profile_service.py:34](../../backend/app/services/profile_service.py#L34):
    `_ACTIVE_TOURNAMENT_STATES = ("open", "in_progress")`.
  - Test que inserta `state="in_progress"`:
    `backend/tests/unit/test_profile_service.py:487`.
- **HALLAZGO (supervisión humana)**: el vocabulario de estado está **fragmentado**:
  - `tournament_service` solo transiciona `draft → open → finished/cancelled` y **nunca
    asigna `in_progress`** (búsqueda en
    [tournament_service.py](../../backend/app/services/tournament_service.py): asignaciones
    `state =` en líneas 132/177/289/455 → draft, open, cancelled; ninguna `in_progress`).
  - `match_service` asigna el torneo a `finished`
    ([match_service.py:183](../../backend/app/services/match_service.py#L183)) pero no a
    `in_progress`.
  - El **frontend** usa el literal `'active'` para "En curso"
    ([Dashboard.jsx:19-27](../../frontend/src/pages/Dashboard.jsx#L19-L27),
    `STATE_LABELS.active = "En curso"`; `tournamentApi`/`tournamentHandlers` lo replican).
- **Implicación para `/tasks`**: dado que ningún servicio asigna `in_progress` hoy, "Torneos
  activos" podría salir **siempre 0** con datos reales hasta que exista la transición
  open→in_progress (arranque de torneo). La tarea de implementación debe **una de dos**:
  1. (Preferido) Unificar el frontend a `in_progress` y documentar dónde el dominio pasa un
     torneo a "en curso" (o tratar `open` con bracket generado como "en curso" si el equipo
     lo confirma), **pidiendo aprobación humana** antes de tocar `tournament_service`.
  2. Mapear en el dashboard `active`(frontend) ↔ `in_progress`(backend) en la capa de schema,
     sin tocar el dominio.
  Esta decisión de dominio **queda fuera del alcance de planificación** y se marca como TODO
  con aprobación humana (Constitution III/IV). El plan asume `in_progress` como token de
  contrato del dashboard.
- **Alternativas consideradas**: `'active'` (precedente frontend) — rechazado por el humano a
  favor de `in_progress`.
- **RESOLUCIÓN (T030, 2026-06-09)**: Se eligió la **Opción 2** (mapear en la capa del
  dashboard, **sin tocar el dominio**). Hechos verificados durante la implementación:
  `tournament_service.start_tournament` asigna `state="active"`
  ([tournament_service.py:507](../../backend/app/services/tournament_service.py#L507)) y
  `TournamentState.ACTIVE = "active"`
  ([schemas/tournament.py:19](../../backend/app/schemas/tournament.py#L19)); ningún punto del
  dominio asigna `in_progress`. Para no romper el contrato del dashboard ({`in_progress`,`open`})
  sin requerir aprobación humana para alterar transiciones (Constitution III/IV), el **read layer**
  del dashboard trata ambos tokens como "en curso" mediante
  `stats_service.IN_PROGRESS_STATES = ("in_progress","active")` y **normaliza** el token emitido a
  `in_progress` en `dashboard_service.get_my_tournaments` (y lo cuenta en "Torneos activos").
  El **frontend** queda unificado a `in_progress` por construcción: la nueva `Dashboard.jsx`
  consume el endpoint (que ya normaliza) y `TournamentCard.jsx` mapea `in_progress`→"En curso";
  no quedan literales `'active'` en la ruta del dashboard. El test
  `test_my_tournaments_treats_domain_active_token_as_in_progress` fija este comportamiento.
  La unificación del dominio (`active`→`in_progress`) o la introducción de una transición
  open→in_progress siguen **fuera de alcance** y requieren aprobación humana.

---

## Decisión 3 — Origen del feed: tabla `activity_feed` escrita en caliente

- **Decisión**: Crear la tabla **`activity_feed`** y **escribir un evento en el momento de la
  acción** desde los servicios existentes. **NO** se deriva el feed de las tablas existentes
  en lectura.
- **Rationale**: El prompt lo especifica de forma explícita y literal
  ([05-dashboard.txt:44-52, 61-90](../../prompts/second/05-dashboard.txt)): tabla
  `activity_feed` con columnas `id, actor_id, event_type, tournament_id, created_at`, un
  `activity_service` de "escritura y lectura del feed", y eventos "generados en el backend al
  ocurrir la acción". Por Constitution IV (usar la herramienta tal como la indica el humano,
  sin buscar una solución "más elegante"), el prompt **anula** la asunción de la spec
  (línea 160) de derivar el feed de `matches/participants/invitations/tournaments`.
- **Contradicción documentada**: spec Assumptions vs prompt. Se sigue el prompt; la spec
  reconoce que "la planificación técnica decide la estrategia de consulta".
- **Tipos de evento** (cerrados para esta versión):
  `MATCH_WIN`, `TOURNAMENT_JOIN`, `TOURNAMENT_INVITE`, `TOURNAMENT_CREATE`.
- **Puntos de instrumentación** (cambios **aditivos**, sin alterar contratos existentes):
  | event_type | Dónde se emite | Actor |
  |------------|----------------|-------|
  | `MATCH_WIN` | `match_service` al confirmar resultado (winner != None, `is_bye=False`) | usuario dueño del `winner_participant_id` |
  | `TOURNAMENT_JOIN` | `tournament_service` al aceptar invitación / inscribirse (crear `Participant`) | usuario que se une |
  | `TOURNAMENT_INVITE` | `tournament_service` al crear `Invitation` | `inviter_user_id` |
  | `TOURNAMENT_CREATE` | `tournament_service` al crear `Tournament` | `organizer_id` |
- **Alternativas consideradas**: vista materializada / UNION en lectura (lo que sugería la
  spec) — descartado por contradecir el prompt.

---

## Decisión 4 — Límite del feed = 6 eventos

- **Decisión**: El feed devuelve los **6** eventos más recientes (cronológico, desc).
- **Rationale**: El prompt lo fija dos veces: "los últimos 6 eventos cronológicos"
  ([05-dashboard.txt:45](../../prompts/second/05-dashboard.txt)) y el test unitario nombrado
  `test_activity_service.py # límite de 6`. La spec lo deja abierto ("decenas… el límite
  exacto se decide en planificación"); el prompt manda.
- **Filtro de visibilidad**: solo eventos cuyo `actor_id` sea el propio usuario **o** un
  amigo `accepted` en el momento de la consulta (FR-019). Sin paginación ni filtros (FR/prompt).

---

## Decisión 5 — Reglas de cálculo de métricas (stats_service)

Fuente: prompt §"Métricas — reglas de cálculo"
([05-dashboard.txt:30-42](../../prompts/second/05-dashboard.txt)) + spec FR-003..FR-008.

- **Torneos activos**: `COUNT` de torneos `state='in_progress'` donde el usuario es
  `Participant` (`removed=False`). **Variación semanal**: comparar con cuántos torneos
  estaban en curso hace exactamente 7 días, **recalculado** (no se almacena snapshot). Dado
  que no existe historial de estado, se aproxima contando torneos en los que el usuario
  participaba y que estaban "en curso hace 7 días" según `started_at <= now-7d` y
  (`finished_at IS NULL OR finished_at > now-7d`). **HALLAZGO**: depende de `started_at`
  ([tournament.py:26](../../backend/app/models/tournament.py#L26)), que existe en el modelo
  pero su poblado depende de la transición open→in_progress (ver Decisión 2). Si no hay
  datos previos, la variación es **neutra** (sin signo), nunca un porcentaje sin sentido
  (edge case spec línea 74).
- **Victorias totales**: `COUNT` de `matches` con `is_bye=False`, `state != 'pending'` y
  `winner_participant_id` ∈ participaciones del usuario. **Winrate** = victorias /
  (victorias + derrotas), excluyendo byes; **0%** y sin división por cero si no hay partidas
  (FR-008). Patrón de join Match→Participant→User tomado de
  [standings_service.py:46-82](../../backend/app/services/standings_service.py#L46-L82).
- **Mejor streak**: mayor nº de victorias consecutivas **dentro de un mismo torneo**,
  ordenadas por `resolved_at` (fecha de confirmación). Se devuelve con `tournament_id` y
  `tournament_name` del torneo donde se logró; cuando la racha abarca varias, se asocia al
  torneo de la **última** victoria de la racha (regla determinista, spec Assumption línea
  156). Usa `Match.resolved_at`
  ([match.py:34](../../backend/app/models/match.py#L34)).
- **Nº de amigos**: ver Decisión 1.
- **Sin caché**: todo se calcula en la petición (FR-007, prompt línea 42).

---

## Decisión 6 — "Tiempo transcurrido" del feed

- **Decisión**: El backend devuelve `created_at` (ISO-8601, UTC) por evento; el **frontend**
  formatea el tiempo relativo ("hace X minutos/horas") y cae a fecha absoluta pasado un
  umbral. No se envía texto pre-renderizado desde el backend.
- **Rationale**: Mantiene el backend libre de i18n/locale y reutiliza el patrón ya usado en
  el frontend (`new Date(...).toLocaleString()` en
  [Dashboard.jsx:167](../../frontend/src/pages/Dashboard.jsx#L167)). Simplicidad
  (Constitution IV).

---

## Decisión 7 — Resiliencia ante referencias inexistentes (FR-022)

- **Decisión**: En lectura del feed, `LEFT JOIN` a `users` y `tournaments`; si el actor o el
  torneo ya no existe (cuenta eliminada/torneo borrado), la entrada se devuelve con el campo
  correspondiente en `null` y el frontend renderiza el nombre **sin enlace** (o la omite),
  sin romper la página. Para amigos eliminados, además dejan de ser `accepted` (FK
  `ondelete=CASCADE` en `friendships`), por lo que sus eventos dejan de pasar el filtro de
  visibilidad (edge case spec línea 77).
- **Rationale**: FR-022 + escenario 7 de US3. La FK `activity_feed.tournament_id` usará
  `ondelete=SET NULL` para no perder el evento del actor cuando se borra el torneo.

---

## Decisión 8 — Auditoría de dependencias (Constitution I)

- **Decisión**: **Sin dependencias nuevas.** Toda la pila requerida por el prompt ya está
  instalada y auditada en 001–004: FastAPI, SQLAlchemy(async), Alembic, Pydantic v2,
  pydantic-settings, httpx, pytest, pytest-asyncio, pytest-cov (backend); React, React
  Router v6, Vitest, @testing-library/*, msw (frontend).
- **Rationale**: No se introduce nueva superficie de ataque ni se requiere investigación CVE
  adicional para esta feature. Cualquier `pip install` o `npm install` nuevo durante la
  implementación **debe** detenerse y pedir supervisión humana con su análisis CVE
  (Constitution I). El endpoint reutiliza `get_current_user`
  ([auth.py](../../backend/app/api/routes/auth.py)) y filtra estrictamente por
  `current_user.id` (FR-023): no acepta `user_id` por parámetro.

---

## Resumen de NEEDS CLARIFICATION

| Ítem | Estado |
|------|--------|
| FR-025 (4ª tarjeta) | **RESUELTO** → "Nº de amigos" (Decisión 1, aprobación humana) |
| Token "en curso" | **RESUELTO** → `in_progress` (Decisión 2, aprobación humana) + HALLAZGO de unificación frontend |
| Origen del feed (spec vs prompt) | **RESUELTO** → tabla `activity_feed` escrita en caliente (Decisión 3) |
| Límite del feed | **RESUELTO** → 6 (Decisión 4) |
| Formato "tiempo transcurrido" | **RESUELTO** → relativo en frontend (Decisión 6) |

No quedan `NEEDS CLARIFICATION` abiertos.
