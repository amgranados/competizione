---
description: "Task list for feature 005 — Dashboard"
---

# Tasks: Dashboard

**Input**: Design documents from `/specs/005-user-dashboard/`
**Prerequisites**: plan.md (required), spec.md (user stories), research.md, data-model.md, contracts/dashboard.openapi.yaml, quickstart.md

**Tests**: INCLUDED. Constitution II (TDD First) is NON-NEGOTIABLE and `quickstart.md` defines the Red→Green→Refactor test map. Every test task is written and made to FAIL before its implementation task.

**Organization**: Tasks are grouped by user story (P1, P2, P3) to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1 / US2 / US3 (maps to spec.md user stories)
- All paths are repo-relative. Backend lives in `backend/`, frontend in `frontend/`.

## Path Conventions

- **Backend**: `backend/app/...`, tests in `backend/tests/...`
- **Frontend**: `frontend/src/...`, tests in `frontend/tests/...`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the environment is ready; no new dependencies (research.md Decisión 8).

- [ ] T001 Verify backend toolchain runs from `backend/` (`pytest`, `ruff check .`, `alembic upgrade head`) and frontend runs from `frontend/` (`npm test`, `npm run dev`) per `specs/005-user-dashboard/quickstart.md`. Do NOT add any new pip/npm dependency — if one seems required, STOP and request human CVE review (Constitution I).
- [ ] T002 [P] Confirm migration head is `e2a4b5c7d9f1_notification_friendship_fk` in `backend/app/db/migrations/versions/` (the new `activity_feed` revision will hang off it per data-model.md).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The `activity_feed` table + model + write/read service are shared by US1 (no — only US3) and the instrumentation hooks. These MUST exist before US3 and before any event instrumentation. US1 and US2 do not depend on this phase.

**⚠️ CRITICAL**: US3 (feed) cannot begin until this phase is complete. US1/US2 may proceed independently of it.

- [ ] T003 [P] Create `ActivityFeed` SQLAlchemy model in `backend/app/models/activity_feed.py` per data-model.md (cols `id`, `actor_id` FK→users ON DELETE CASCADE, `event_type` non-native Enum {MATCH_WIN, TOURNAMENT_JOIN, TOURNAMENT_INVITE, TOURNAMENT_CREATE} with `create_constraint=True`, `tournament_id` FK→tournaments ON DELETE SET NULL nullable, `created_at` tz-aware default now(utc); index `idx_activity_actor_created` on `(actor_id, created_at)`). Follow the style of `backend/app/models/friendship.py`.
- [ ] T004 Register `ActivityFeed` in `backend/app/models/__init__.py` so Alembic autogenerate/imports see it (depends on T003).
- [ ] T005 Create Alembic migration `<rev>_add_activity_feed.py` in `backend/app/db/migrations/versions/` with `down_revision = "e2a4b5c7d9f1"`: `CREATE TABLE activity_feed` + the enum CHECK constraint + `idx_activity_actor_created`; `downgrade()` drops the table/index/constraint. No `ALTER TABLE` on existing tables (depends on T003, T004). Verify it applies and reverts: `alembic upgrade head` then `alembic downgrade -1`.

**Checkpoint**: `activity_feed` table exists and round-trips. US3 foundation ready.

---

## Phase 3: User Story 1 - Saludo y tarjetas de estadísticas (Priority: P1) 🎯 MVP

**Goal**: Post-login landing shows a personalized greeting + fixed subtitle + 4 stat cards (Torneos activos con variación semanal, Victorias totales + winrate, Mejor streak + torneo, Nº de amigos), computed hot from the user's own history.

**Independent Test**: Authenticate as a user with tournament/match history, open the dashboard, and verify the greeting includes the nickname, the fixed subtitle appears, and the 4 cards show values consistent with the user's real data; a brand-new user sees neutral values (0, no delta, no streak tournament) with no errors and no ZeroDivision.

### Tests for User Story 1 (write FIRST, ensure they FAIL) ⚠️

- [ ] T006 [P] [US1] Unit tests for stats in `backend/tests/unit/test_stats_service.py` covering: torneos activos counts only `in_progress` where user participates (FR-003); weekly delta = active_now − active_7d_ago, neutral/None when no history (FR-004, edge case); wins exclude byes (FR-005); winrate = wins/(wins+losses)·100, returns 0 with no games and no ZeroDivision (FR-005/FR-008); best streak = max consecutive wins within one tournament ordered by `resolved_at`, returning `tournament_id`+`tournament_name` of the streak's LAST win (FR-006, Assumption); friends_count = COUNT accepted friendships both directions excluding `deleted_at` (FR-025); empty user → all neutral, no error (FR-008, SC-003).
- [ ] T007 [P] [US1] Frontend unit test in `frontend/tests/unit/StatsCard.test.jsx`: renders positive (`+1`), negative (`-2`) and zero/neutral (no sign) weekly variation, and winrate `0%` without breaking when no games.

### Implementation for User Story 1

- [ ] T008 [US1] Implement `stats_service.py` in `backend/app/services/stats_service.py`: `get_stats(session, user)` returning active tournaments + weekly_delta, total wins + games_played + winrate, best streak + tournament ref, friends_count — per research.md Decisión 5. Reuse the Match→Participant→User join pattern from `backend/app/services/standings_service.py` and the `_pair_filter` friends pattern from `backend/app/services/friends_service.py`. Active = `state='in_progress'`; never accepts an external `user_id` (FR-023) (makes T006 pass).
- [ ] T009 [P] [US1] Add `StatsCards`, `ActiveTournamentsStat`, `WinsStat`, `StreakStat` Pydantic v2 schemas to `backend/app/schemas/dashboard.py` matching `contracts/dashboard.openapi.yaml` (nullable `weekly_delta`, nullable `winrate`, nullable streak tournament fields).
- [ ] T010 [P] [US1] Create `StatsCard.jsx` in `frontend/src/components/StatsCard.jsx`: a metric card rendering value + signed variation (+/−/neutral), handling winrate `0%` gracefully (makes T007 pass).

**Checkpoint**: stats_service + StatsCard are independently testable. (Greeting/subtitle/page wiring is completed once the `/api/dashboard` endpoint exists in T020–T023; US1 cards render standalone now.)

---

## Phase 4: User Story 2 - Mis torneos en curso y próximos (Priority: P2)

**Goal**: Dashboard shows cards for the user's `in_progress`/`open` tournaments (name, state, format, players_count, current_round or start_at) plus a "Ver todos" link to the Tournaments section.

**Independent Test**: With a user in ≥1 in-progress and 1 upcoming tournament, the section shows both as cards with correct fields; finished/cancelled and non-participated tournaments are excluded; empty state shows when none; "Ver todos" navigates to Tournaments.

### Tests for User Story 2 (write FIRST, ensure they FAIL) ⚠️

- [ ] T011 [P] [US2] Add to `backend/tests/integration/test_dashboard_routes.py` cases for `my_tournaments`: includes the user's `in_progress`/`open` tournaments with correct name/state/format/players_count and `current_round` (in_progress) or `start_at` (open); excludes finished/cancelled and tournaments the user is not in (FR-010, SC-004).

### Implementation for User Story 2

- [ ] T012 [P] [US2] Add `TournamentCard` Pydantic schema to `backend/app/schemas/dashboard.py` per contract (`id`, `name`, `state` enum {in_progress, open}, `format` enum {round_robin, single_elim}, `players_count`, nullable `current_round`, nullable `start_at`).
- [ ] T013 [US2] Implement "my tournaments" query in `backend/app/services/dashboard_service.py` (or a helper consumed by it): select tournaments where the user is a non-removed `Participant` and `state IN ('in_progress','open')`, with players_count and round/start_at, ordered sensibly (makes T011 pass; depends on T012).
- [ ] T014 [P] [US2] Create `TournamentCard.jsx` in `frontend/src/components/TournamentCard.jsx`: renders name, state label ("En curso"/"Próximo"), format, players_count, and current_round (in_progress) or start_at (open).

**Checkpoint**: my_tournaments query + TournamentCard testable. US1 and US2 both work independently of US3.

---

## Phase 5: User Story 3 - Feed de actividad reciente (Priority: P3)

**Goal**: Chronological feed (newest first, ≤6) of the user's and friends' events (MATCH_WIN, TOURNAMENT_JOIN, TOURNAMENT_INVITE, TOURNAMENT_CREATE), each showing actor, action, linked tournament and relative time; actor/tournament are clickable; resilient to deleted users/tournaments.

**Independent Test**: With user A having friend B and non-friend D, generate the four event types; A's feed shows A's and B's events but not D's, newest-first, with actor/tournament links, and renders resiliently when a referenced tournament/user no longer exists.

### Tests for User Story 3 (write FIRST, ensure they FAIL) ⚠️

- [ ] T015 [P] [US3] Unit tests in `backend/tests/unit/test_activity_service.py`: `record(...)` inserts a row (actor/type/tournament/created_at); `list_recent` returns at most 6; ordered newest-first (FR-020); excludes events whose actor is neither the user nor an accepted friend (FR-019, SC-005); includes the user's OWN events (FR-015); removed/anonymized friend (`deleted_at`/no `accepted`) events excluded (edge case); deleted tournament (`tournament_id` NULL) → resilient entry (FR-022).
- [ ] T016 [P] [US3] Frontend unit test in `frontend/tests/unit/ActivityFeed.test.jsx`: renders each event type with actor/action/tournament/relative time; resilient entry when actor or tournament missing (text without link, no crash, FR-022); actor link → `/users/:nickname`, tournament link → `/tournaments/:id` (FR-018).
- [ ] T017 [P] [US3] Add instrumentation tests verifying events are emitted at the action: extend `backend/tests/unit/test_match_service.py` (MATCH_WIN on confirmed result, winner set, not a bye) and add/extend `backend/tests/unit/test_tournament_service.py` for TOURNAMENT_JOIN (new Participant), TOURNAMENT_INVITE (new Invitation), TOURNAMENT_CREATE (new Tournament) per research.md Decisión 3.

### Implementation for User Story 3

- [ ] T018 [US3] Implement `activity_service.py` in `backend/app/services/activity_service.py`: `record(session, actor_id, event_type, tournament_id=None)` (write) and `list_recent(session, user, limit=6)` (read) — `list_recent` filters by actor ∈ {user + accepted friends}, LEFT JOINs `users`/`tournaments` for resilience (null id → no link), orders by `created_at` DESC, limit 6 (makes T015 pass; depends on T003).
- [ ] T019 [US3] Instrument existing services (additive, no contract changes): call `activity_service.record(...)` from `backend/app/services/match_service.py` (MATCH_WIN) and `backend/app/services/tournament_service.py` (TOURNAMENT_JOIN, TOURNAMENT_INVITE, TOURNAMENT_CREATE) at the points in research.md Decisión 3 (makes T017 pass; depends on T018).
- [ ] T020 [P] [US3] Add `ActivityEvent`, `ActorRef`, `TournamentRef` Pydantic schemas to `backend/app/schemas/dashboard.py` per contract (`actor.exists`, nullable `actor.id`, nullable `tournament`).
- [ ] T021 [P] [US3] Create `ActivityFeed.jsx` in `frontend/src/components/ActivityFeed.jsx`: chronological list, per-type rendering, relative-time formatting in the client (research.md Decisión 6), clickable actor/tournament with resilient no-link fallback (makes T016 pass).

**Checkpoint**: All three stories independently functional.

---

## Phase 6: Endpoint, Page Wiring & Cross-Cutting (integrates all stories)

**Purpose**: Single `GET /api/dashboard` endpoint and the rewritten Dashboard page that compose stats + my_tournaments + feed into one response/render (FR-024, SC-001). This phase ties the stories together; the endpoint's response is built from whichever services are complete.

### Tests (write FIRST, ensure they FAIL) ⚠️

- [ ] T022 [P] Add to `backend/tests/integration/test_dashboard_routes.py`: `GET /api/dashboard` without auth → 401 (FR-023); authenticated → 200 with a full `DashboardResponse` (greeting with nickname, fixed subtitle, stats, my_tournaments, activity) matching `contracts/dashboard.openapi.yaml`; user A never sees non-friend data/events (isolation, SC-005); brand-new user → 200 with neutral stats and empty arrays (SC-008).
- [ ] T023 [P] Rewrite `frontend/tests/integration/Dashboard.test.jsx` (currently covers the old tournament-creation hub) to the new spec, using a new `frontend/tests/mocks/dashboardHandlers.js` msw handler for `GET /api/dashboard`: shows "Hola, <nickname>" + fixed subtitle (FR-001/002, SC-002); 4 cards with mock values (FR-003..006/025); my_tournaments cards + "Ver todos" navigates to Tournaments (FR-009/013, SC-009); feed ≤6 ordered with links (FR-015..020); informative empty states with no error (FR-014/021, SC-008).

### Implementation

- [ ] T024 Add `DashboardResponse` schema (greeting, subtitle, stats, my_tournaments, activity) to `backend/app/schemas/dashboard.py` per contract (depends on T009, T012, T020).
- [ ] T025 Implement `dashboard_service.py` in `backend/app/services/dashboard_service.py`: orchestrate greeting (nickname with safe default, FR-001) + fixed subtitle (FR-002) + `stats_service.get_stats` + my_tournaments query + `activity_service.list_recent`, all from `current_user.id` (FR-023) (depends on T008, T013, T018).
- [ ] T026 Implement `GET /api/dashboard` route in `backend/app/api/routes/dashboard.py` using `get_current_user` (from `backend/app/api/routes/auth.py`), returning `DashboardResponse`; never accepts an external `user_id` (FR-023) (depends on T024, T025; makes T022 pass).
- [ ] T027 Register the dashboard router in `backend/app/main.py` (depends on T026).
- [ ] T028 [P] Create `dashboardApi.js` in `frontend/src/api/dashboardApi.js`: `getDashboard()` using native `fetch` with `credentials:"include"` (pattern from existing `frontend/src/api/*.js`).
- [ ] T029 Rewrite `frontend/src/pages/Dashboard.jsx`: consume `getDashboard()` and render greeting + 4 `StatsCard` + "Mis torneos" (`TournamentCard` list + "Ver todos" link) + `ActivityFeed`, with informative empty states (depends on T010, T014, T021, T028; makes T023 pass).

---

## Phase 7: Polish & Validation

- [ ] T030 Resolve or document the state-token finding (research.md Decisión 2): unify frontend `'active'` ↔ backend `in_progress` (e.g. in `frontend/src/pages/Dashboard.jsx`/`tournamentApi`) OR map `active`↔`in_progress` in the dashboard schema layer. Do NOT modify `tournament_service` state transitions without explicit human approval (Constitution III/IV). Record the decision in the feature notes.
- [ ] T031 [P] Run `ruff check .` from `backend/` and fix any lint in new/changed files.
- [ ] T032 Run full `pytest` (backend) and `npm test` (frontend); confirm all new tests pass and none of 001–004's suites regress.
- [ ] T033 Run the manual smoke from `specs/005-user-dashboard/quickstart.md` (US1/US2/US3 + new-user empty states, zero errors, SC-008) and confirm the Definición de hecho gates.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: After Setup. BLOCKS US3 and instrumentation only. US1/US2 do NOT depend on it.
- **US1 (Phase 3)**: After Setup. Independent of US2/US3 and of Phase 2.
- **US2 (Phase 4)**: After Setup. Independent of US1/US3.
- **US3 (Phase 5)**: After Foundational (Phase 2). Independent of US1/US2.
- **Integration (Phase 6)**: After the services/schemas/components of whichever stories are in scope (T024 needs the per-story schemas; T025 needs the per-story services; T029 needs the per-story components).
- **Polish (Phase 7)**: After integration.

### Within Each User Story

- Tests are written and FAIL before implementation (Constitution II).
- Models → services → schemas/endpoints. Components can be built in parallel with backend.

### Parallel Opportunities

- T001/T002 (Setup) in parallel.
- T003 (model) then T004→T005 (migration chain).
- Per story, the [P] test tasks and the frontend component tasks run in parallel with backend service work (different files).
- With a team: after Phase 2, US1 / US2 / US3 can be developed concurrently by three developers, converging at Phase 6.

---

## Parallel Example: User Story 1

```bash
# Write tests first, in parallel (different files):
Task: "Unit tests for stats in backend/tests/unit/test_stats_service.py"
Task: "Frontend unit test in frontend/tests/unit/StatsCard.test.jsx"

# Then implement in parallel where files differ:
Task: "Implement stats_service.py in backend/app/services/stats_service.py"
Task: "Add stats schemas to backend/app/schemas/dashboard.py"
Task: "Create StatsCard.jsx in frontend/src/components/StatsCard.jsx"
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 Setup.
2. Phase 3 US1 (stats_service + StatsCard + schemas).
3. Minimal Phase 6 wiring (endpoint returning at least greeting + stats; T024–T029 scoped to US1) to render the page.
4. STOP and VALIDATE US1 independently.

### Incremental Delivery

- Setup → US1 (+ minimal endpoint/page) → demo MVP.
- Add US2 (my_tournaments) → extend endpoint/page → demo.
- Add Foundational (Phase 2) + US3 (feed + instrumentation) → extend endpoint/page → demo.
- Polish (Phase 7) → resolve state-token finding, lint, full suites, smoke.

---

## Notes

- [P] = different files, no incomplete-task dependency.
- `backend/app/schemas/dashboard.py` is touched by T009/T012/T020/T024 — these are sequential edits to the same file (not all [P] against each other); the [P] markers are relative to tasks in other files.
- No new dependencies (Constitution I). Any required `pip install`/`npm install` → STOP for human CVE review.
- Verify each test fails before implementing. Commit after each task or logical group.
