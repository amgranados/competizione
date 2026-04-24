---
description: "Task list for feature 002-tournament-management: Creación y gestión de torneos con calendario automático"
---

# Tasks: Creación y gestión de torneos con calendario automático

**Input**: Design documents from `specs/002-tournament-management/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: TDD es **OBLIGATORIO** por la Constitución (Principio II, NON-NEGOCIABLE). Cada tarea de test debe fallar (Red) antes de escribir la implementación asociada (Green).

**Organization**: Tareas agrupadas por user story en su orden de prioridad. Se omiten las historias fuera de alcance esta iteración: **US2** (verificación por API) y **US7** (gestión de cuenta LoL vinculada) — ambas dependen de la vinculación de cuenta Riot, declarada fuera de scope en [spec.md](./spec.md) y [plan.md § Scope](./plan.md). La numeración `US1, US3, US4, US5, US6` se preserva tal cual aparece en `spec.md` para conservar la trazabilidad.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo con otras `[P]` del mismo bloque (ficheros distintos, sin dependencias pendientes).
- **[Story]**: `US1`, `US3`, `US4`, `US5`, `US6` para tareas de historia. Setup, Foundational y Polish no llevan etiqueta de historia.
- Todos los paths son relativos a la raíz del repositorio.

## Path Conventions

Estructura fijada en [plan.md § Project Structure](./plan.md) (Variante B — backend API + frontend SPA):

- Backend: `backend/app/**`, `backend/tests/**`
- Frontend: `frontend/src/**`, `frontend/tests/**`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Preparar subdirectorios nuevos y extender la configuración existente del repo 001 sin introducir dependencias runtime.

- [ ] T001 Crear subdirectorios nuevos vacíos: `backend/app/services/riot_api/` (con `__init__.py` vacío), y asegurar que existen `backend/app/models/`, `backend/app/schemas/`, `backend/app/services/`, `backend/app/api/routes/`, `backend/tests/unit/`, `backend/tests/integration/`, `frontend/src/api/`, `frontend/src/context/`, `frontend/src/hooks/`, `frontend/src/components/`, `frontend/src/pages/`, `frontend/tests/mocks/`, `frontend/tests/unit/`, `frontend/tests/integration/` (ya creados en 001; añadir `.gitkeep` donde haga falta).
- [ ] T002 [P] Añadir `RIOT_API_KEY=` (opcional, comentada) a `backend/.env.example` con comentario explicando que su ausencia fuerza `MockRiotAPIClient` y deja log explícito ([quickstart.md § Env vars](./quickstart.md)).
- [ ] T003 [P] Extender `Settings` en `backend/app/core/config.py` con `RIOT_API_KEY: str | None = None` (sin cambios en el resto de campos de 001).

**Checkpoint**: Entorno listo. Ningún paquete nuevo instalado; `respx` queda diferida (ver [research.md § Dependencias diferidas](./research.md)).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestructura transversal que **toda** user story de 002 consume: cliente Riot (Protocol + Mock + factory por env) y hook genérico de polling frontend. Notificaciones e infraestructura de BBDD se incluyen en US1 porque nacen junto con el primer flujo que las produce (invitación).

**⚠️ CRITICAL**: Ninguna user story puede empezar hasta que esta fase esté completa.

### Tests (Red — deben fallar antes de implementar)

- [ ] T004 [P] Test unitario `backend/tests/unit/test_riot_api_client.py::test_mock_client_returns_configured_match_result` en `backend/tests/unit/test_riot_api_client.py`: el `MockRiotAPIClient` devuelve los datos configurados por test fixture para `get_match_by_tournament_code()` y `validate_riot_id()`.
- [ ] T005 [P] Test unitario `backend/tests/unit/test_riot_api_client.py::test_factory_returns_mock_when_api_key_missing_and_logs`: el factory devuelve `MockRiotAPIClient` cuando `settings.RIOT_API_KEY is None` y emite un log `INFO` con la cadena `Using MockRiotAPIClient: RIOT_API_KEY not set` (usar `caplog`).
- [ ] T006 [P] Test unitario `frontend/tests/unit/usePolling.test.js`: con fake timers, `usePolling(fetcher, 10000)` llama a `fetcher` al montar, luego cada 10 s exactos; al desmontar limpia el intervalo (no se produce más invocaciones).

### Implementation (Green)

- [ ] T007 [P] Implementar `RiotAPIClient` Protocol en `backend/app/services/riot_api/client.py` con los dos métodos definidos en el stack (`validate_riot_id(game_name, tag_line) -> bool`, `get_match_by_tournament_code(tournament_code) -> MatchResult | None`) y un dataclass `MatchResult` mínimo (campos suficientes para la validación FR-036: `participants: list[ParticipantInfo]`, `duration_seconds: int`, `game_mode: str`, `start_timestamp: datetime`). Exportar también un `get_riot_api_client(settings) -> RiotAPIClient` que devuelva `MockRiotAPIClient()` cuando `settings.RIOT_API_KEY is None` (log INFO con la cadena exacta) y `HttpRiotAPIClient(settings.RIOT_API_KEY)` en caso contrario. El símbolo `HttpRiotAPIClient` se importa **sólo** dentro de la rama; no se implementa hasta la iteración futura (DEFER documentado con `# TODO iteración futura`).
- [ ] T008 [P] Implementar `MockRiotAPIClient` en `backend/app/services/riot_api/mock_client.py` con atributos configurables (`configured_match_results: dict[str, MatchResult]`, `configured_riot_ids: set[tuple[str, str]]`) y los dos métodos del Protocol devolviendo esos datos. Sin dependencias externas.
- [ ] T009 [P] Implementar hook `usePolling(fetcher, intervalMs = 10000)` en `frontend/src/hooks/usePolling.js`: `useEffect` monta `setInterval`, al desmontar `clearInterval`; expone `{ data, error, refresh }` donde `refresh` permite forzar un fetch inmediato (usado por las vistas tras acciones locales — ver [quickstart.md § Frontend patterns](./quickstart.md)).

**Checkpoint**: Cliente Riot preparado (no cableado aún a ningún endpoint) y polling genérico disponible. User stories pueden empezar.

---

## Phase 3: User Story 1 — Organizar un torneo de extremo a extremo (Priority: P1) 🎯 MVP

**Goal**: Un usuario autenticado puede crear un torneo, invitar amigos, abrir inscripciones, recibir confirmaciones, eliminar participantes pre-inicio, iniciar el torneo con ≥2 participantes y ver el calendario (round-robin completo o primera ronda de single-elim) con códigos de sala únicos por enfrentamiento. Las invitaciones expiran a las 48h, se pueden cancelar. Se crean notificaciones in-app que el usuario puede listar y marcar leídas mediante polling.

**Independent Test**: [quickstart.md](./quickstart.md) — desde la UI un organizador completa: crear torneo → invitar 3 amigos → los 3 aceptan → iniciar torneo → ver calendario con códigos. En backend: `pytest backend/tests -k "tournament or invitation or notification or calendar"` en verde.

**FR cubiertos**: FR-005, FR-006, FR-007, FR-008, FR-009, FR-011, FR-012, FR-013, FR-014, FR-015, FR-016, FR-017, FR-018, FR-019, FR-023, FR-024, FR-025, FR-026, FR-027, FR-028, FR-029, FR-030, FR-031, FR-032, FR-033, FR-051 (sólo parte "próximos"), FR-057 (notificación de invitación).

**HD-1** (ya resuelta): esta iteración permite invitar a **cualquier usuario registrado** sin check de amistad ([research.md § HD-1](./research.md)).

### Tests unitarios de algoritmos (Red) — en paralelo

- [ ] T010 [P] [US1] Test `test_round_robin_even_pairs_everyone_once` en `backend/tests/unit/test_calendar_service.py`: con N=4 (`p1,p2,p3,p4`), el resultado contiene 6 matches no-bye, cada par `{pi, pj}` aparece exactamente una vez, y hay 3 rondas con 2 matches cada una.
- [ ] T011 [P] [US1] Test `test_round_robin_odd_every_player_rests_exactly_once` en `backend/tests/unit/test_calendar_service.py`: con N=5, hay 5 rondas; cada real tiene exactamente un match con `is_bye=True` (propiedad fairness-bye, SC-006).
- [ ] T012 [P] [US1] Test `test_round_robin_is_deterministic` en `backend/tests/unit/test_calendar_service.py`: misma lista de participantes en el mismo orden produce exactamente el mismo calendario en dos invocaciones consecutivas.
- [ ] T013 [P] [US1] Test `test_single_elim_with_6_participants_assigns_2_byes_to_most_recent` en `backend/tests/unit/test_calendar_service.py`: con 6 participantes con `accepted_at` creciente (p1 el primero, p6 el último), la primera ronda tiene 2 matches reales entre `p1–p2`/`p3–p4` (orden estable por inscripción ASC) y 2 byes sobre `p5` y `p6` (SC-007).
- [ ] T014 [P] [US1] Test `test_single_elim_no_next_round_generated_on_creation` en `backend/tests/unit/test_calendar_service.py`: tras `generate_single_elim_first_round`, el torneo sólo tiene matches en `round_number = 1` (FR-027).
- [ ] T015 [P] [US1] Test `test_round_robin_bye_has_no_tournament_code` en `backend/tests/unit/test_calendar_service.py`: cualquier match con `is_bye=True` tiene `tournament_code is None` y `code_created_at is None` (FR-048 / prompt).
- [ ] T016 [P] [US1] Test `test_each_non_bye_match_gets_unique_tournament_code` en `backend/tests/unit/test_calendar_service.py`: todos los `tournament_code` generados son UUIDv4 válidos y distintos entre sí para el mismo torneo (FR-031).

### Tests integración backend (Red) — en paralelo

- [ ] T017 [P] [US1] Test `test_create_tournament_as_draft` en `backend/tests/integration/test_tournament_routes.py`: `POST /tournaments` con payload válido → 201, body con `state="draft"`, `organizer_id=<user autenticado>`, `id` UUIDv4.
- [ ] T018 [P] [US1] Test `test_create_tournament_rejects_invalid_format` en `backend/tests/integration/test_tournament_routes.py`: `format="random"` → 422.
- [ ] T019 [P] [US1] Test `test_open_registration_draft_to_open` en `backend/tests/integration/test_tournament_routes.py`: `POST /tournaments/{id}/open` sobre torneo en `draft` por el organizador → 200, `state="open"`. Rechazo 409 si el estado no es draft.
- [ ] T020 [P] [US1] Test `test_invite_user_creates_pending_invitation_with_48h_expiry` en `backend/tests/integration/test_tournament_routes.py`: `POST /tournaments/{id}/invitations` → 201; `expires_at` ≈ `created_at + 48h` (tolerancia ±5 s); notificación `invitation_received` creada para el invitado.
- [ ] T021 [P] [US1] Test `test_cannot_invite_same_user_twice_while_pending` en `backend/tests/integration/test_tournament_routes.py`: segunda invitación al mismo usuario en estado pending → 409.
- [ ] T022 [P] [US1] Test `test_accept_invitation_creates_participant` en `backend/tests/integration/test_tournament_routes.py`: `POST /invitations/{iid}/accept` con el invitado autenticado → 200, `state="accepted"`, existe `Participant(tournament, user, accepted_at=now)`. Notificación `invitation_accepted` para el organizador.
- [ ] T023 [P] [US1] Test `test_reject_invitation` en `backend/tests/integration/test_tournament_routes.py`: → 200, `state="rejected"`, notificación `invitation_rejected` al organizador.
- [ ] T024 [P] [US1] Test `test_cancel_pending_invitation_by_organizer` en `backend/tests/integration/test_tournament_routes.py`: → 200, `state="cancelled"`, notificación `invitation_cancelled` al invitado.
- [ ] T025 [P] [US1] Test `test_accept_expired_invitation_returns_410` en `backend/tests/integration/test_tournament_routes.py`: fijar `expires_at` en el pasado con helper de test → 410 y la invitación queda como `expired` en BBDD (check-on-read).
- [ ] T026 [P] [US1] Test `test_remove_participant_while_draft` en `backend/tests/integration/test_tournament_routes.py`: `DELETE /tournaments/{id}/participants/{pid}` por el organizador sobre torneo en draft → 204; el participante desaparece del listado.
- [ ] T027 [P] [US1] Test `test_remove_participant_after_start_rejected_409` en `backend/tests/integration/test_tournament_routes.py`.
- [ ] T028 [P] [US1] Test `test_start_tournament_rejects_below_minimum_participants` en `backend/tests/integration/test_tournament_routes.py`: con 1 participante → 409 (SC-009).
- [ ] T029 [P] [US1] Test `test_start_round_robin_generates_all_matches_and_codes` en `backend/tests/integration/test_tournament_routes.py`: con 4 participantes, tras `POST /tournaments/{id}/start` → 200, `state="active"`; `GET /tournaments/{id}/schedule` devuelve 3 rondas × 2 matches, todos con `tournament_code` no nulo y únicos.
- [ ] T030 [P] [US1] Test `test_start_single_elim_generates_first_round_with_byes` en `backend/tests/integration/test_tournament_routes.py`: con 6 participantes single-elim → primera ronda con 2 matches reales + 2 byes; los byes tienen `tournament_code is None`.
- [ ] T031 [P] [US1] Test `test_start_locks_format_change` en `backend/tests/integration/test_tournament_routes.py`: tras iniciar, `PATCH /tournaments/{id}` con nuevo formato → 409 (FR-019).
- [ ] T032 [P] [US1] Test `test_tournament_detail_hidden_for_outsider_returns_404` en `backend/tests/integration/test_tournament_routes.py`: usuario no organizador, no participante y sin invitación → 404 (patrón anti-enumeración).
- [ ] T033 [P] [US1] Test `test_list_notifications_for_current_user` en `backend/tests/integration/test_notifications_routes.py`: `GET /notifications` devuelve sólo las del usuario autenticado, ordenadas por `created_at DESC`; filtro `?unread=true` excluye las leídas.
- [ ] T034 [P] [US1] Test `test_mark_notification_read` en `backend/tests/integration/test_notifications_routes.py`: `PATCH /notifications/{id}/read` → 200, `read_at` fijado.
- [ ] T035 [P] [US1] Test `test_mark_other_users_notification_returns_404` en `backend/tests/integration/test_notifications_routes.py`.

### Tests integración frontend (Red) — en paralelo

- [ ] T036 [P] [US1] MSW handlers para `tournaments` y `invitations` en `frontend/tests/mocks/tournamentHandlers.js` (listar, crear, detalle, abrir, iniciar, invitar, aceptar, rechazar, cancelar).
- [ ] T037 [P] [US1] MSW handlers para `notifications` en el mismo fichero o en `frontend/tests/mocks/notificationHandlers.js` (listar, marcar leída).
- [ ] T038 [P] [US1] Test integración `frontend/tests/integration/Dashboard.test.jsx`: lista los torneos del usuario (organizador + participante) y las invitaciones pendientes; botón "Nuevo torneo" abre el formulario.
- [ ] T039 [P] [US1] Test integración `frontend/tests/integration/TournamentDetail.test.jsx` — sub-casos: (a) organizador crea torneo → aparece en detalle con estado draft; (b) organizador invita → tras polling aparece en la lista de invitaciones; (c) organizador pulsa "Iniciar" con <2 participantes → UI muestra error; (d) con ≥2 participantes → estado pasa a active y se ven los matches/codes; (e) participante no organizador no ve botones de gestión.

### Implementation (Green)

#### Backend — modelos y schemas

- [ ] T040 [P] [US1] Modelo `Tournament` en `backend/app/models/tournament.py` con columnas según [data-model.md § Tournament](./data-model.md) (UUIDv4, nombre, start_at nullable, format enum, state enum, organizer_id FK User, created/started/finished/cancelled_at).
- [ ] T041 [P] [US1] Modelo `Participant` en `backend/app/models/participant.py` con `UNIQUE (tournament_id, user_id)`, `accepted_at`, flag `removed` (soft delete pre-start).
- [ ] T042 [P] [US1] Modelo `Invitation` en `backend/app/models/invitation.py` con estados enum, `expires_at`, `responded_at`, `inviter_user_id` (= organizer_id esta iteración).
- [ ] T043 [P] [US1] Modelo `Match` en `backend/app/models/match.py` con `round_number`, `bracket_position` nullable, `player1_id`, `player2_id` nullable, `is_bye`, `tournament_code` nullable, `code_created_at` nullable, `state` enum (`pending`, `manual`; valor `verified_api` reservado en el enum pero sin transición activa), `winner_participant_id` nullable, `resolved_at` nullable.
- [ ] T044 [P] [US1] Modelo `Notification` en `backend/app/models/notification.py` con `type` enum (valores listados en [data-model.md § Notification](./data-model.md)), FKs nullables a tournament/match/invitation.
- [ ] T045 [P] [US1] Schemas Pydantic en `backend/app/schemas/tournament.py`: enums `TournamentFormat`/`TournamentState`/`InvitationState`, `TournamentCreate`, `TournamentUpdate`, `Tournament`, `ParticipantSummary`, `Invitation`, `InvitationCreate`, `RoundMatchSummary`, `Schedule`, `StandingEntry`, `MatchState`.
- [ ] T046 [P] [US1] Schemas Pydantic en `backend/app/schemas/notification.py`: enum `NotificationType`, modelo `Notification`.

#### Backend — servicios

- [ ] T047 [US1] `backend/app/services/calendar_service.py`: función `generate_round_robin(participants: list[Participant]) -> list[Round]` siguiendo el circle method (pseudocódigo en [research.md § Algoritmo round-robin](./research.md)). Ordena entrada por `accepted_at ASC, id ASC`. Byes con `tournament_code = None`.
- [ ] T048 [US1] Misma `backend/app/services/calendar_service.py`: `generate_single_elim_first_round(participants) -> Round` con byes asignados a los de `accepted_at` más reciente. Genera `tournament_code` (UUIDv4) y `code_created_at = now` sólo para matches no-bye.
- [ ] T049 [US1] Función placeholder `close_round_and_generate_next(tournament, closed_round_number)` en el mismo fichero: detección de ronda completada + generación de la siguiente ronda. La implementación completa (con avance de ganadores) se cierra en US3 — este commit sólo añade la firma y docstring, con `raise NotImplementedError` (test que lo usa vendrá en US3).
- [ ] T050 [US1] `backend/app/services/notification_service.py` con `create_notification(user_id, type, tournament_id=None, match_id=None, invitation_id=None) -> Notification`, `list_for_user(user_id, only_unread)`, `mark_read(notification_id, user_id)`.
- [ ] T051 [US1] `backend/app/services/tournament_service.py` — métodos:
  - `create(organizer_id, payload) -> Tournament`.
  - `get_visible_to_user(tournament_id, user_id)` (404 si no organizador/participante/invitado pendiente).
  - `list_for_user(user_id, state_filter)`.
  - `open_registration(tournament_id, user_id)` (draft→open; sólo organizador).
  - `invite(tournament_id, invitee_id, user_id)` (crea Invitation con `expires_at = now + 48h`, crea notificación `invitation_received`; valida que el invitee no es ya participante ni tiene pending).
  - `cancel_invitation(tournament_id, invitation_id, user_id)` (→ cancelled, notificación `invitation_cancelled`).
  - `accept_invitation(invitation_id, user_id)` (check expiration on read; crea Participant; notifica al organizador).
  - `reject_invitation(invitation_id, user_id)`.
  - `remove_participant(tournament_id, participant_id, user_id)` (bloquea si state ∉ {draft, open}; marca `removed=true`).
  - `start(tournament_id, user_id)` (valida ≥2 participantes activos no removidos; invoca `calendar_service.generate_*`; crea todos los Match; fija `state='active'`, `started_at=now`; crea notificación `tournament_started` para todos los participantes + `match_generated` para cada jugador no-bye).

#### Backend — rutas y migración

- [ ] T052 [US1] `backend/app/api/routes/tournaments.py` con los endpoints:
  - `POST /tournaments`, `GET /tournaments`, `GET /tournaments/{id}`, `POST /tournaments/{id}/open`, `POST /tournaments/{id}/start`.
  - `POST /tournaments/{id}/invitations`, `GET /tournaments/{id}/invitations`, `POST /tournaments/{id}/invitations/{iid}/cancel`.
  - `GET /invitations`, `POST /invitations/{iid}/accept`, `POST /invitations/{iid}/reject`.
  - `DELETE /tournaments/{id}/participants/{pid}`.
  - `GET /tournaments/{id}/schedule` (lista de rondas; participantes/organizador ven `tournament_code` dentro de `RoundMatchSummary`; filtrado de `tournament_code` para terceros que no estén en el match se aplica en la serialización).
- [ ] T053 [US1] `backend/app/api/routes/notifications.py` con `GET /notifications` (filtro `?unread=true`) y `PATCH /notifications/{id}/read`.
- [ ] T054 [US1] Registrar `tournament_router` y `notification_router` en `backend/app/main.py`.
- [ ] T055 [US1] Revisión Alembic única `initial_tournament_schema` en `backend/app/db/migrations/versions/`: crea tablas `tournaments`, `participants`, `invitations`, `matches`, `notifications`. Ejecutar `alembic upgrade head` en la BBDD de test antes de correr la integración.

#### Frontend

- [ ] T056 [P] [US1] `frontend/src/api/tournamentApi.js` con funciones `listMine`, `create`, `getById`, `openRegistration`, `start`, `invite`, `listInvitations`, `cancelInvitation`, `listMyInvitations`, `accept`, `reject`, `removeParticipant` usando el `request` helper de 001 (`credentials: "include"`).
- [ ] T057 [P] [US1] `frontend/src/api/notificationApi.js` con `list(unread)` y `markRead(id)`.
- [ ] T058 [P] [US1] `frontend/src/context/NotificationContext.jsx` usando `usePolling(notificationApi.list({unread:true}), 10000)` y exponiendo `{ notifications, markRead, refresh }`.
- [ ] T059 [P] [US1] `frontend/src/hooks/useTournament.js` (recibe `tournamentId`, usa `usePolling` para `getById` cada 10 s + expone `refresh` inmediato tras acciones locales).
- [ ] T060 [P] [US1] `frontend/src/pages/Dashboard.jsx`: lista los torneos del usuario (organizador/participante) y las invitaciones pendientes recibidas; botón "Nuevo torneo" abre formulario que llama a `tournamentApi.create`.
- [ ] T061 [P] [US1] `frontend/src/pages/TournamentDetail.jsx`: muestra estado, participantes, invitaciones (si es organizador), formulario de invitar, botones "Abrir inscripciones" / "Iniciar" condicionados por estado y rol, lista de matches con `tournament_code` (visible sólo a organizador y jugadores del match).
- [ ] T062 [US1] Registrar rutas `/dashboard`, `/tournaments/:id` en `frontend/src/main.jsx` envueltas en `<ProtectedRoute>`.

**Checkpoint**: US1 entregable (MVP). Un usuario puede crear un torneo, invitar, recibir confirmaciones, eliminar participantes pre-inicio, iniciar el torneo y ver el calendario generado con códigos. Notificaciones operativas con polling.

---

## Phase 4: User Story 3 — Registrar resultado manualmente con etiqueta permanente (Priority: P2)

**Goal**: El organizador puede registrar el resultado de un enfrentamiento pendiente indicando el ganador. El match queda marcado `manual` de forma inamovible. En eliminación directa avanza al ganador a la siguiente ronda, cerrando rondas y generando las siguientes hasta que la final resuelve → torneo `finished`. En round-robin, el match queda cerrado y la clasificación se recalcula (la vista se entrega en US4).

**Independent Test**: Partiendo de un torneo iniciado (output de US1), el organizador registra resultados por UI y backend hasta completar el torneo. `pytest backend/tests -k "match or manual"` en verde.

**FR cubiertos**: FR-020, FR-040, FR-041, FR-042, FR-043, FR-044, FR-045, FR-046, FR-049, FR-050, FR-052, FR-054, FR-057 (notificación tournament_finished y match_resolved), FR-058 (acceso read-only implícito al estar terminal).

### Tests (Red) — en paralelo

- [ ] T063 [P] [US3] Test `test_register_manual_result_marks_match_as_manual` en `backend/tests/unit/test_match_service.py`: llamada al servicio con winner válido → `state='manual'`, `winner_participant_id=<winner>`, `resolved_at=now` ± 1 s.
- [ ] T064 [P] [US3] Test `test_manual_result_is_immutable` en `backend/tests/unit/test_match_service.py`: segunda llamada al servicio sobre el mismo match (ya manual) → excepción de dominio (bucket 409); el match no cambia (FR-042).
- [ ] T065 [P] [US3] Test `test_manual_cannot_use_non_player_as_winner` en `backend/tests/unit/test_match_service.py`: `winner_participant_id` que no es player1/player2 → excepción (409).
- [ ] T066 [P] [US3] Test `test_manual_cannot_register_on_future_round` en `backend/tests/unit/test_match_service.py`: match cuya ronda aún no existe (en single-elim) → excepción (FR-045, FR-046).
- [ ] T067 [P] [US3] Test `test_manual_in_single_elim_advances_winner_to_next_round` en `backend/tests/unit/test_match_service.py`: tras el último match de la ronda 1, la ronda 2 se genera con los ganadores (preservando posición de bracket) y `tournament_code` nuevo por match.
- [ ] T068 [P] [US3] Test `test_bye_is_resolved_as_manual_on_round_close_single_elim` en `backend/tests/unit/test_match_service.py`: al cerrarse una ronda con byes (single-elim), los byes pasan a `manual` con `winner=player1`; el jugador bye aparece en la ronda siguiente.
- [ ] T069 [P] [US3] Test `test_grand_final_resolution_transitions_tournament_to_finished` en `backend/tests/unit/test_match_service.py`: en single-elim tras resolver la final, `tournament.state='finished'` y `finished_at` fijado (FR-050).
- [ ] T070 [P] [US3] Test `test_round_robin_last_result_transitions_tournament_to_finished` en `backend/tests/unit/test_match_service.py`: al cerrarse el último match pendiente (sin byes pendientes) en round-robin, transición automática a `finished` (FR-020). Notificación `tournament_finished` a todos.
- [ ] T071 [P] [US3] Test `test_manual_result_creates_match_resolved_notifications_for_both_players` en `backend/tests/unit/test_match_service.py`.
- [ ] T072 [P] [US3] Test `test_manual_result_route_organizer_only` en `backend/tests/integration/test_match_routes.py`: jugador no organizador → 403; no-autenticado → 401.
- [ ] T073 [P] [US3] Test `test_manual_result_route_returns_match_with_tag` en `backend/tests/integration/test_match_routes.py`: `POST /matches/{id}/manual-result` con winner válido → 200, body con `state='manual'`, `winner_participant_id` esperado.
- [ ] T074 [P] [US3] Test `test_get_match_hides_tournament_code_for_non_player_non_organizer` en `backend/tests/integration/test_match_routes.py`: un participante del torneo que no es player de ese match ve `tournament_code: null`.
- [ ] T075 [P] [US3] MSW handler `matchHandlers.js` en `frontend/tests/mocks/matchHandlers.js` (detalle + manual-result).
- [ ] T076 [P] [US3] Test integración `frontend/tests/integration/MatchDetail.test.jsx`: (a) organizador ve botón "Registrar resultado"; (b) participante jugador del match ve el detalle pero no ese botón; (c) tras registrar → UI muestra etiqueta "Introducido manualmente" permanente.

### Implementation (Green)

- [ ] T077 [US3] `backend/app/services/match_service.py` con:
  - `register_manual_result(match_id, winner_participant_id, acting_user_id)` (valida organizer, winner ∈ players, match.state == 'pending', ronda ≤ current round; marca manual + resolved_at; notifica ambos jugadores `match_resolved`; delega en `close_round_and_generate_next` si aplica).
  - `advance_winner_single_elim(match)` (inserta al ganador en el bracket_position de la ronda siguiente si ya existe; si no, se creará al cerrarse la ronda).
  - `close_round_and_generate_next(tournament, round_number)` (si todos los matches de la ronda están resueltos: resuelve byes, genera ronda siguiente o transita `finished`; genera `tournament_code` para los nuevos matches).
  - `finalize_if_last_match(tournament)` (round-robin y single-elim; transición `active → finished`, `finished_at=now`, notificación `tournament_finished` a todos los participantes).
- [ ] T078 [US3] Completar `calendar_service.close_round_and_generate_next` (reemplazar `NotImplementedError` de T049) delegando en `match_service` o compartiendo lógica (decisión de refactor dentro del ciclo Green/Refactor — priorizar mantener en `match_service` para centralizar transiciones de estado).
- [ ] T079 [P] [US3] Schemas en `backend/app/schemas/match.py`: `Match`, `ManualResultRequest`. Serializador que elide `tournament_code` según el rol del lector.
- [ ] T080 [US3] `backend/app/api/routes/matches.py` con `GET /matches/{id}` y `POST /matches/{id}/manual-result`.
- [ ] T081 [US3] Registrar `match_router` en `backend/app/main.py`.
- [ ] T082 [P] [US3] `frontend/src/api/matchApi.js` con `getById`, `registerManualResult`.
- [ ] T083 [P] [US3] `frontend/src/pages/MatchDetail.jsx`: detalle del match, `tournament_code` visible sólo si viene en el payload; botón "Registrar resultado" visible sólo para organizador cuando `state='pending'`. Tras registrar, UI muestra etiqueta "Introducido manualmente" inmutable.
- [ ] T084 [US3] Ruta `/matches/:id` en `frontend/src/main.jsx` envuelta en `<ProtectedRoute>`; enlace desde `TournamentDetail`.

**Checkpoint**: Se pueden completar torneos de principio a fin por la vía manual. `state='finished'` se alcanza automáticamente.

---

## Phase 5: User Story 4 — Seguir la clasificación y el cuadro en tiempo real (Priority: P2)

**Goal**: Cualquier participante/organizador consulta la tabla de clasificación (round-robin) o el cuadro (single-elim) con resultados confirmados, estado de cada match (pendiente/manual), próximos enfrentamientos con código de sala y resultados pasados. El orden en round-robin aplica las 4 reglas de desempate (victorias → directo → fecha inscripción → id).

**Independent Test**: Con un torneo round-robin con resultados manuales (output de US3), `GET /tournaments/{id}/standings` devuelve la tabla correctamente ordenada. Con un torneo single-elim, `GET /tournaments/{id}/bracket` devuelve el cuadro actualizado. La UI refresca mediante polling cada 10 s (test con fake timers) y aplica refresh inmediato tras acciones locales (SC-003).

**FR cubiertos**: FR-047, FR-048, FR-051, FR-052, FR-053, FR-054.

### Tests (Red) — en paralelo

- [ ] T085 [P] [US4] Test `test_points_are_wins_and_byes_dont_score` en `backend/tests/unit/test_standings_service.py`: montar torneo con 3 resueltos y 1 bye para un jugador → puntos = victorias; el jugador con bye tiene `byes=1` pero sus puntos igualan sólo sus victorias (FR-048, SC-005).
- [ ] T086 [P] [US4] Test `test_tiebreak_head_to_head` en `backend/tests/unit/test_standings_service.py`: dos jugadores con mismos puntos; el que ganó el directo queda arriba.
- [ ] T087 [P] [US4] Test `test_circular_tie_breaks_by_inscription_date` en `backend/tests/unit/test_standings_service.py`: tres jugadores A,B,C con mismos puntos y ciclo A>B>C>A; orden final = `accepted_at ASC`.
- [ ] T088 [P] [US4] Test `test_tie_with_same_inscription_breaks_by_participant_id` en `backend/tests/unit/test_standings_service.py`: dos participantes con idéntico `accepted_at` → orden por `participant.id ASC` (edge case spec).
- [ ] T089 [P] [US4] Test `test_standings_service_is_deterministic` en `backend/tests/unit/test_standings_service.py`: misma configuración dos invocaciones → mismo orden.
- [ ] T090 [P] [US4] Test `test_get_schedule_shows_all_rounds_and_states` en `backend/tests/integration/test_tournament_routes.py`: `GET /tournaments/{id}/schedule` incluye el estado (`pending` o `manual`) de cada match; participante ve su `tournament_code`, tercero no.
- [ ] T091 [P] [US4] Test `test_get_standings_returns_404_for_single_elim` en `backend/tests/integration/test_tournament_routes.py`.
- [ ] T092 [P] [US4] Test `test_get_bracket_returns_404_for_round_robin` en `backend/tests/integration/test_tournament_routes.py`.
- [ ] T093 [P] [US4] Test `test_get_standings_round_robin_orders_by_rules` en `backend/tests/integration/test_tournament_routes.py`: fixture con escenario de desempate directo → orden esperado.
- [ ] T094 [P] [US4] Test integración `frontend/tests/integration/TournamentDetail.test.jsx` — extensión: (a) formato round-robin renderiza `<StandingsTable>`; (b) formato single-elim renderiza `<TournamentBracket>`; (c) tras `markRead`/action local, se dispara `refresh` inmediato.

### Implementation (Green)

- [ ] T095 [US4] `backend/app/services/standings_service.py::compute(tournament) -> list[StandingEntry]` implementando las 4 reglas de desempate (puntos → directo → inscripción → id). Para el paso directo construir DAG "A vence a B" entre los empatados y detectar ciclos con DFS (ver [data-model.md § StandingEntry](./data-model.md)).
- [ ] T096 [US4] Añadir a `backend/app/api/routes/tournaments.py`:
  - `GET /tournaments/{id}/schedule` (si no está ya expuesto de US1; asegurar formato `Schedule` completo con estados).
  - `GET /tournaments/{id}/standings` (404 si single-elim).
  - `GET /tournaments/{id}/bracket` (404 si round-robin; reutiliza `Schedule`).
- [ ] T097 [P] [US4] `frontend/src/components/StandingsTable.jsx` — recibe lista de `StandingEntry`, muestra rank, nickname, victorias, derrotas, byes, puntos.
- [ ] T098 [P] [US4] `frontend/src/components/TournamentBracket.jsx` — recibe el `Schedule` de single-elim y dibuja el cuadro (CSS grid simple); resalta ganador por match; botón "ir al match" enlaza a `MatchDetail`.
- [ ] T099 [US4] Integrar componentes en `TournamentDetail.jsx` condicionados al `format`; añadir polling (`usePolling` reutilizado) sobre `schedule` y `standings/bracket` según corresponda. Refresh inmediato tras registrar resultado manual (callback del MatchDetail).

**Checkpoint**: Clasificación y cuadro visibles y correctos en tiempo real.

---

## Phase 6: User Story 5 — Modificar el torneo antes de iniciarlo (Priority: P3)

**Goal**: El organizador puede cambiar nombre, fecha y formato mientras el torneo esté en `draft` o `open`. Tras `active` todos estos parámetros quedan bloqueados.

**Independent Test**: Fixture con torneo en `draft` → `PATCH` con cambios permitidos → 200. Mismo torneo en `active` → 409.

**FR cubiertos**: FR-021, FR-022, SC-010.

### Tests (Red) — en paralelo

- [ ] T100 [P] [US5] Test `test_rename_tournament_while_draft` en `backend/tests/integration/test_tournament_routes.py`.
- [ ] T101 [P] [US5] Test `test_change_format_while_open` en `backend/tests/integration/test_tournament_routes.py`.
- [ ] T102 [P] [US5] Test `test_change_start_at_to_null_while_draft` en `backend/tests/integration/test_tournament_routes.py`.
- [ ] T103 [P] [US5] Test `test_modify_after_start_returns_409` en `backend/tests/integration/test_tournament_routes.py` (nombre, fecha y formato todos rechazados).
- [ ] T104 [P] [US5] Test `test_modify_by_non_organizer_returns_403` en `backend/tests/integration/test_tournament_routes.py`.
- [ ] T105 [P] [US5] Test integración `frontend/tests/integration/TournamentDetail.test.jsx` — extensión: organizador en draft ve formulario de edición; en active, los controles de edición no se renderizan.

### Implementation (Green)

- [ ] T106 [US5] `tournament_service.update(tournament_id, payload, user_id)` en `backend/app/services/tournament_service.py`: valida organizer + estado ∈ {draft, open}; aplica cambios permitidos; devuelve Tournament.
- [ ] T107 [US5] `PATCH /tournaments/{id}` en `backend/app/api/routes/tournaments.py` consumiendo `TournamentUpdate`.
- [ ] T108 [P] [US5] Formulario de edición en `frontend/src/pages/TournamentDetail.jsx` visible sólo para organizador cuando `state ∈ {draft, open}`.

**Checkpoint**: Modificación pre-inicio operativa y bloqueo post-inicio verificado.

---

## Phase 7: User Story 6 — Cancelar un torneo (Priority: P3)

**Goal**: El organizador puede cancelar un torneo en cualquier estado no terminal. Todos los participantes reciben notificación. El torneo pasa a `cancelled` y queda en solo lectura.

**Independent Test**: Fixture con torneo en cualquier estado no-terminal → `POST /tournaments/{id}/cancel` → 200, `state='cancelled'`. Se crean notificaciones para todos. Desde `finished` → 409.

**FR cubiertos**: FR-055, FR-056, FR-057, FR-058, SC-010 (parcial).

### Tests (Red) — en paralelo

- [ ] T109 [P] [US6] Test `test_cancel_from_draft_transitions_to_cancelled` en `backend/tests/integration/test_tournament_routes.py`.
- [ ] T110 [P] [US6] Test `test_cancel_from_active_transitions_to_cancelled` en `backend/tests/integration/test_tournament_routes.py`.
- [ ] T111 [P] [US6] Test `test_cancel_from_finished_returns_409` en `backend/tests/integration/test_tournament_routes.py`.
- [ ] T112 [P] [US6] Test `test_cancel_creates_notification_for_every_participant` en `backend/tests/integration/test_tournament_routes.py`.
- [ ] T113 [P] [US6] Test `test_cancelled_tournament_rejects_any_state_mutation` en `backend/tests/integration/test_tournament_routes.py`: tras cancelar, `PATCH`, `open`, `start`, `invite`, `manual-result`, etc. → 409.
- [ ] T114 [P] [US6] Test integración `frontend/tests/integration/TournamentDetail.test.jsx` — extensión: organizador ve botón "Cancelar" cuando no terminal; tras cancelar, vista pasa a solo-lectura (sin botones de acción).

### Implementation (Green)

- [ ] T115 [US6] `tournament_service.cancel(tournament_id, user_id)` en `backend/app/services/tournament_service.py`: valida organizer + estado ∉ {finished, cancelled}; transita a `cancelled`, `cancelled_at=now`; crea notificación `tournament_cancelled` para cada participante activo; bloquea mutaciones subsiguientes en todos los puntos de servicio.
- [ ] T116 [US6] `POST /tournaments/{id}/cancel` en `backend/app/api/routes/tournaments.py`.
- [ ] T117 [P] [US6] Botón "Cancelar torneo" en `frontend/src/pages/TournamentDetail.jsx` (organizador only, estado no-terminal) con confirmación en UI.

**Checkpoint**: Todas las historias en scope entregadas. FR-005..FR-033, FR-040..FR-058 implementados.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T118 [P] Actualizar `README.md` de la raíz añadiendo enlace a [quickstart.md](./quickstart.md) de 002 y resumen del flujo MVP.
- [ ] T119 [P] Ejecutar `pytest --cov=app --cov-report=term-missing` en `backend/` y adjuntar el informe. Objetivo mínimo razonable por módulo: `calendar_service` ≥ 95 %, `standings_service` ≥ 95 %, `match_service` ≥ 85 %, `tournament_service` ≥ 85 %, rutas ≥ 80 %.
- [ ] T120 [P] Ejecutar `npm run test:coverage` en `frontend/` y adjuntar el informe. Objetivo: `usePolling` ≥ 95 %, `TournamentDetail`/`MatchDetail` ≥ 80 %.
- [ ] T121 [P] Revisión de autorización transversal (OWASP API1/API3): grep por cada endpoint de `backend/app/api/routes/{tournaments,matches,notifications}.py` verificando que se usa la dependency `get_current_user` y que el servicio filtra por ownership; 404 (no 403) para recursos no visibles al usuario para no filtrar existencia.
- [ ] T122 [P] Revisión de serialización de `tournament_code`: grep confirma que el campo sólo se emite cuando el lector es `organizer_id` o uno de `{player1_id.user_id, player2_id.user_id}`. Test ya cubre (T074) — aquí se documenta y se verifica manualmente la ruta del filtro.
- [ ] T123 [P] Property-test extra de `calendar_service`: script `backend/tests/unit/test_calendar_service.py::test_round_robin_completeness_for_N_up_to_16` que itera `N ∈ {2..16}` y verifica propiedad de completeness y fairness-bye en todos. Complementa los ejemplos puntuales de US1.
- [ ] T124 Validación manual de quickstart: ejecutar el flujo de [quickstart.md § Flujo TDD por user story](./quickstart.md) en un entorno limpio (levantar Postgres local + backend + frontend) y confirmar que el flujo completo US1 → US3 → US4 → US5 → US6 funciona end-to-end.
- [ ] T125 Checklist de Constitución: revisar `research.md § CVE Audit` (sin deps nuevas instaladas → sigue vigente), Principio II (grep: no hay commits con código productivo previos a su test), Principio III (todas las decisiones técnicas con fuente), Principio IV (sin sustituciones de stack), Principio V (ningún import runtime referencia `prompts/`).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** → sin dependencias; debe terminar antes que Foundational.
- **Foundational (Phase 2)** → depende de Phase 1; **bloquea** todas las user stories.
- **US1 (Phase 3)** → depende de Foundational. Habilita todas las demás historias (modelos, notificaciones, calendario).
- **US3 (Phase 4)** → depende de US1 (necesita torneos iniciados con matches).
- **US4 (Phase 5)** → depende de US1 (necesita matches y schedule endpoint). Puede solaparse con US3 (fixtures de test pueden sintetizar resultados sin pasar por US3 endpoints), pero en la práctica conviene ir tras US3.
- **US5 (Phase 6)** → depende sólo de US1 (modificación pre-inicio). Puede paralelizarse con US3/US4.
- **US6 (Phase 7)** → depende sólo de US1 (cancelar en cualquier estado no terminal). Puede paralelizarse con US3/US4/US5.
- **Polish (Phase 8)** → depende de todas las historias.

### Within Each User Story (TDD orden obligatorio)

1. Escribir los tests (Red).
2. Ejecutar y confirmar fallo.
3. Implementar el mínimo para pasar (Green).
4. Refactorizar manteniendo verde.

### Parallel Opportunities

- **Setup**: T002, T003 en paralelo.
- **Foundational**: los tres tests (T004, T005, T006) en paralelo; luego T007, T008, T009 en paralelo.
- **Dentro de US1**: todos los tests unitarios (T010–T016), todos los tests de integración backend (T017–T035) y todos los de frontend mocks/tests (T036–T039) pueden lanzarse en paralelo como bloque Red. Luego los modelos (T040–T044) y schemas (T045–T046) son `[P]` entre sí; los ficheros de frontend (T056–T061) son todos `[P]`.
- **Inter-historias**: tras completar US1, un equipo de ≥2 personas puede tomar US3, US5, US6 en paralelo (ficheros prácticamente disjuntos: `match_service.py` vs. `tournament_service.update()` vs. `tournament_service.cancel()`). US4 es mejor empezar cuando US3 haya establecido la lógica de cierre de ronda.

---

## Parallel Example: User Story 1 (bloque Red)

```bash
# Tests unitarios de calendar_service (Red), en paralelo:
Task: "T010 [P] [US1] test_round_robin_even_pairs_everyone_once"
Task: "T011 [P] [US1] test_round_robin_odd_every_player_rests_exactly_once"
Task: "T013 [P] [US1] test_single_elim_with_6_participants_assigns_2_byes_to_most_recent"

# Tests de integración backend (Red), en paralelo:
Task: "T017 [P] [US1] test_create_tournament_as_draft"
Task: "T022 [P] [US1] test_accept_invitation_creates_participant"
Task: "T029 [P] [US1] test_start_round_robin_generates_all_matches_and_codes"
Task: "T033 [P] [US1] test_list_notifications_for_current_user"

# Tests frontend (Red), en paralelo:
Task: "T036 [P] [US1] MSW tournamentHandlers.js"
Task: "T038 [P] [US1] Dashboard.test.jsx"
Task: "T039 [P] [US1] TournamentDetail.test.jsx"
```

## Parallel Example: User Story 1 (bloque Green)

```bash
# Modelos en paralelo (ficheros distintos):
Task: "T040 [P] [US1] Tournament model en backend/app/models/tournament.py"
Task: "T041 [P] [US1] Participant model en backend/app/models/participant.py"
Task: "T042 [P] [US1] Invitation model en backend/app/models/invitation.py"
Task: "T043 [P] [US1] Match model en backend/app/models/match.py"
Task: "T044 [P] [US1] Notification model en backend/app/models/notification.py"

# Frontend en paralelo (ficheros distintos):
Task: "T056 [P] [US1] tournamentApi.js"
Task: "T057 [P] [US1] notificationApi.js"
Task: "T058 [P] [US1] NotificationContext.jsx"
Task: "T060 [P] [US1] Dashboard.jsx"
Task: "T061 [P] [US1] TournamentDetail.jsx"
```

---

## Implementation Strategy

### MVP First (US1 solamente)

1. Completar Phase 1 (Setup).
2. Completar Phase 2 (Foundational) — crítico.
3. Completar Phase 3 (US1) con TDD estricto.
4. **Parar y validar**: ejecutar `pytest backend/tests -k "tournament or invitation or calendar or notification"` y `npm run test:run` en `frontend/`; correr la app localmente y completar el flujo crear → invitar → aceptar → iniciar → ver calendario.
5. Demo / deploy opcional — los matches se ven "pendientes" porque aún no hay resultado manual; es un MVP funcional.

### Incremental Delivery

1. Setup + Foundational ⇒ base.
2. + US1 ⇒ **MVP**: organizar torneos + calendario generado.
3. + US3 ⇒ registro de resultados y avance hasta `finished`.
4. + US4 ⇒ clasificación y cuadro en tiempo real.
5. + US5 ⇒ modificación pre-inicio.
6. + US6 ⇒ cancelación.
7. Polish ⇒ cobertura, property-tests, auditoría.

### Parallel Team Strategy

- Dev A: US1 (crítico — desbloquea todo).
- Tras US1:
  - Dev A: US3 (match_service, match routes).
  - Dev B: US5 (tournament_service.update + PATCH route).
  - Dev C: US6 (tournament_service.cancel + cancel route).
- Tras US3:
  - Dev A o B: US4 (standings_service + schedule/standings/bracket endpoints + componentes frontend).

---

## Notes

- **Constitución II (NO NEGOCIABLE)**: cada tarea de test debe estar en rojo antes de la implementación asociada. Si se detecta código nuevo sin test previo en rojo, revertir y rehacer.
- **Constitución I**: no instalar dependencias que no estén auditadas en `research.md § CVE Audit`. `respx` queda fuera de esta iteración; si en algún momento alguien propone instalarla antes de tiempo, pedir supervisión humana.
- **Constitución III**: decisiones técnicas que surjan durante la implementación se documentan como notas en `research.md` con su fuente. Los diagramas van a `contracts/*.puml`.
- **Constitución IV**: estructura de carpetas, librerías y flags son los fijados por el humano en `prompts/second/02-torneo.txt`; no sustituirlos. Reserva `RIOT_API_KEY`/`RiotAPIClient` implementados tal cual pedidos aunque no se cableen a ningún endpoint esta iteración.
- **Constitución V**: ningún import productivo referencia `prompts/` en runtime; sólo specs y documentación.
- `[P]` = ficheros distintos sin dependencias pendientes.
- Confirmar que cada test falla antes de pasar a la implementación asociada.
- Commit después de cada tarea o bloque Red/Green/Refactor para mantener trazabilidad.
- Al cerrar US6 antes de Polish: el scope funcional de 002 está cerrado; Polish son mejoras de cobertura, auditoría y validación manual.
