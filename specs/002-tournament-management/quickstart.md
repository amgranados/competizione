# Quickstart — Tournament Management (feature 002)

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md) · **Data model**: [data-model.md](./data-model.md)

Guía de arranque y flujo TDD para 002, complementaria a la de 001 (que sigue siendo el punto de entrada para levantar el entorno). Esta guía asume que 001 ya está funcionando.

---

## Prerrequisitos

- Backend 001 funcionando (PostgreSQL + FastAPI arrancan limpiamente; `pytest` verde).
- Frontend 001 funcionando (`npm run dev` arranca, tests Vitest en verde).
- Rama git activa: `002-tournament-management`.

## Env vars (backend)

Heredadas de 001 (`DATABASE_URL`, `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES=15`, `REFRESH_TOKEN_EXPIRE_DAYS=7`, `FRONTEND_ORIGIN`).

**Nueva opcional**:

| Variable | Default | Uso en esta iteración |
|----------|---------|------------------------|
| `RIOT_API_KEY` | *unset* | Reservada para la iteración futura. En 002 no se instancia ningún cliente productivo; si no está definida, el factory del `RiotAPIClient` devuelve `MockRiotAPIClient` **y deja un log explícito** (`logger.info("Using MockRiotAPIClient: RIOT_API_KEY not set")`). Si está definida, el factory la pasaría a `HttpRiotAPIClient` (DEFER). |

Añadir la variable a `.env.example` sin valor por defecto:

```env
# Feature 002 — opcional, reservada para iteración futura (integración API de Riot).
# Si no se define, se usa MockRiotAPIClient (sólo en tests; no hay endpoint que lo consuma en esta iteración).
RIOT_API_KEY=
```

## Migraciones

Tras confirmar los tests en rojo de los modelos (Principio II), generar una nueva revisión Alembic por entidad o agrupar según pase de test:

```bash
cd backend
alembic revision --autogenerate -m "002: tournament, participant, invitation, match, notification"
alembic upgrade head
```

La revisión **no debe** crear la tabla `riot_accounts` (DEFER); si `--autogenerate` la añade (porque el modelo exista stubbed), editar manualmente antes de aplicar.

## Flujo TDD por user story

Siguiendo el orden propuesto en [research.md § TDD Workflow](./research.md#-tdd-workflow-principio-ii):

1. **US1 (P1) — Organizar un torneo E2E**: empezar por `backend/tests/integration/test_tournament_routes.py::test_create_tournament_as_draft`. Ejecutar `pytest backend/tests/integration/test_tournament_routes.py -x`. Debe estar rojo.
2. Implementar mínimo en `backend/app/schemas/tournament.py`, `backend/app/models/tournament.py`, `backend/app/services/tournament_service.py`, `backend/app/api/routes/tournaments.py`.
3. Volver a ejecutar hasta verde. Refactorizar sin añadir funcionalidad.
4. Avanzar al siguiente test del bloque (abrir inscripciones, invitar, aceptar, iniciar, …).
5. **US3 (P2) — Resultado manual**: empezar por `test_match_routes.py::test_manual_result_marks_match_as_manual`.
6. **US4 (P2) — Clasificación y cuadro**: empezar por los tests unitarios puros (`test_standings_service.py`) antes de tocar endpoints.
7. **US5 (P3), US6 (P3)**: al final, cuando el camino feliz esté verde.

**Regla invariante**: ningún commit introduce código productivo sin su test correspondiente en rojo antes.

## Arranque del backend

Sin cambios respecto a 001:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate  # o .venv\Scripts\activate en Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

El contrato OpenAPI de esta feature queda disponible en `/docs` (FastAPI auto-genera a partir de los Pydantic schemas y routers). Los ficheros `contracts/*.openapi.yaml` son la **fuente de verdad** del contrato; cualquier divergencia se resuelve corrigiendo el backend, no el contrato (salvo que la divergencia sea una decisión intencional registrada en `plan.md` o `research.md`).

## Arranque del frontend

```bash
cd frontend
npm install
npm run dev
```

### Frontend patterns (polling)

- El hook `usePolling(fetcher, intervalMs = 10000)` encapsula `setInterval` y `clearInterval` en `useEffect`. Test unitario con fake timers.
- `NotificationContext` lo usa para mantener la bandeja; las páginas `TournamentDetail` y `MatchDetail` lo usan para refrescar calendario/clasificación.
- Tras una acción local del usuario (registrar resultado, cancelar torneo), la página dispara un **refresh inmediato** del fetcher afectado antes del siguiente tick — así SC-003 (<5 s) queda cubierto para el propio usuario incluso con polling a 10 s.

## Ejecución de tests

Backend:

```bash
cd backend
pytest                     # todo
pytest backend/tests/unit  # unitarios de algoritmos
pytest -k calendar         # solo calendar_service
pytest --cov=app --cov-report=term-missing
```

Frontend:

```bash
cd frontend
npm run test:run
npm run test:coverage
```

## Tocar `prompts/` (Principio V)

No. La carpeta `prompts/` es input histórico. No se añaden rutas, módulos, ni imports que la referencien en runtime. Los specs, planes e implementación sí la citan como **fuente documental** (esto es aceptable: es documentación de trazabilidad, no código productivo).

## Cuando aparezca la feature de Riot (iteración futura)

Lista de cosas que quedan "cableadas pero apagadas" esta iteración y que se activan entonces:

1. Crear `backend/app/models/riot_account.py` + revisión Alembic.
2. Añadir rutas de vinculación/desvinculación (`/users/me/riot-account`).
3. Activar FR-010 (check de cuenta vinculada en `tournament_service.invite()`).
4. Implementar `HttpRiotAPIClient` — instalar `respx` en `requirements.txt` (con CVE audit nuevo en ese momento) y escribir los tests de `test_match_service.py::test_verify_result_*`.
5. Exponer `POST /matches/{id}/verify`.
6. Activar la transición `pending → verified_api` en el enum `MatchState`.

Ninguna de estas seis activaciones requiere cambios estructurales en los datos ya creados por 002: se añaden sin migrar destruir.
