# Phase 0 — Research & Decisions: Tournament Management

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

Este documento consolida las decisiones técnicas necesarias antes del diseño (Fase 1), el CVE audit (Principio I), el esquema TDD (Principio II) y las preguntas pendientes al humano (Principio III). Todas las decisiones no fijadas por el prompt del humano se justifican aquí con fuentes (Principio III).

---

## § Human decisions

### HD-1 — Sistema de amistades en las invitaciones ✅ RESUELTA (2026-04-24)

**Contexto**: `spec.md § Assumptions` declara: *"La aplicación dispone (o dispondrá, fuera del alcance de esta feature) de un sistema de amistades..."*. En el repositorio actual no existe ningún módulo de amistades ni la spec 001-user-auth lo introduce. FR-009 dice que el organizador *"puede invitar a usuarios añadidos como amigos"*.

**Opciones evaluadas**:

| Opción | Implica |
|--------|---------|
| A. Construir un sistema de amistades mínimo ahora | Ampliar drásticamente el scope; spec no lo detalla (lista de amigos, requests, aceptar, bloquear). Fuera del espíritu de "no reinventar" y del scope que el humano ya recortó. |
| **B. Permitir invitar a cualquier usuario registrado; reactivar el check de amistad junto con la feature de amistades** | Iteración entregable ya; FR-009 se cumple parcialmente (invitación a usuarios, sin check de amigos). Reentrada sin coste estructural. |
| C. Bloquear todo el flujo de invitaciones | Bloquea US1 completo; el torneo no podría arrancar. Opción no viable para avanzar. |

**Decisión humana (2026-04-24)**: **B** — confirmada por el humano. En esta iteración cualquier usuario registrado puede ser invitado; el check de amistad se reintroducirá cuando exista el servicio de amistades, como un filtro adicional en `tournament_service.invite()`. No requiere cambios estructurales posteriores.

---

## § CVE Audit (Principio I)

**Principio I (Constitución, v1.0.0)**: *"A basic CVE research must be done for every dependency used in the project BEFORE installing it or using it"*.

### Dependencias ya instaladas (heredadas de 001)

Ya auditadas en `specs/001-user-auth/research.md § CVE Audit` y fijadas con versiones seguras. Esta feature **no sube** ninguna versión y **no añade** dependencias runtime.

### Dependencias nuevas mencionadas por el prompt

| Dependencia | Tipo | Estado en esta iteración | CVE audit |
|-------------|------|--------------------------|-----------|
| `respx` | test-only (mock de `httpx`) | **Diferida**: se usará cuando escribamos tests para `HttpRiotAPIClient` (fuera de alcance de 002). | Audit pendiente hasta la instalación. La Constitución obliga a auditar **antes** de instalar, no antes de mencionar en un plan. Se auditará en el momento de añadir `respx` a `requirements.txt`. |

**Conclusión del audit**: sin instalaciones nuevas en esta iteración ⇒ sin acciones de seguridad pendientes esta iteración.

### Superficie de seguridad introducida por la feature (chequeo complementario)

Aunque no hay deps nuevas, la feature introduce lógica sensible; revisamos vectores comunes:

| Vector | Mitigación aplicada | Fuente |
|--------|---------------------|--------|
| Acceso no autorizado a torneos ajenos | Todos los endpoints validan que el usuario autenticado es organizador o participante según corresponda. Ver `data-model.md § Autorización`. | OWASP API1:2023 Broken Object Level Authorization (https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/). |
| Fuga de `tournament_code` a quien no es jugador/organizador | Endpoints de match filtran el campo `tournament_code` según el rol del peticionario. | OWASP API3:2023 Broken Object Property Level Authorization. |
| Manipulación del estado vía cliente (p. ej. marcar "Verificado por API" sin API) | Enum cerrado en Pydantic; sólo el servicio interno muta `state`. Valor `verified_api` **reservado** pero no aceptado aún por ningún endpoint en 002. | Pydantic v2 docs — `Literal` / `Enum` validators. |
| Inyección SQL a través de filtros | Uso exclusivo de SQLAlchemy con bindings y Pydantic para parsear query params. | SQLAlchemy 2.x — Core Expression Language; parametric SQL. |
| CSRF sobre endpoints que modifican estado (crear torneo, registrar resultado) | Herencia 001: cookies `SameSite=lax` + `credentials: "include"` + origin allowlist por CORS (`FRONTEND_ORIGIN`). Las rutas no usan formularios HTML; sólo JSON con `Content-Type: application/json`. | OWASP CSRF Cheat Sheet (https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html). |
| Enumeración de torneos privados por ID UUID | UUID v4 ≈ 122 bits de entropía; imposible enumerar por fuerza bruta. | RFC 4122 §4.4. |

**Resultado**: sin hallazgos abiertos que requieran escalado al humano.

---

## § TDD Workflow (Principio II)

Todo código productivo nace de un test fallido. Orden por FR, agrupado por user story:

### Ciclo Red → Green → Refactor por user story

**US1 (P1) — Organizar un torneo E2E**:

1. **Red**: `test_tournament_routes.py::test_create_tournament_as_draft` espera `POST /tournaments` → 201 con `state="draft"` y `organizer_id=<user>`.
2. **Green**: crear mínimo `TournamentCreate` schema, `tournament_service.create()`, ruta. Sin validaciones extra.
3. **Refactor**: extraer constantes de estado; tipar con enum.
4. Repetir para: abrir inscripción (`test_open_registration_from_draft`), invitar (`test_invite_user`), aceptar invitación (`test_accept_invitation`), rechazar (`test_reject_invitation`), cancelar invitación pre-expiración (`test_cancel_pending_invitation`), expiración (`test_accept_expired_invitation_fails_with_410`), eliminar participante pre-inicio (`test_remove_participant_while_draft`), iniciar torneo con <2 participantes (`test_start_rejected_below_minimum`), iniciar torneo válido (`test_start_generates_matches_round_robin`, `test_start_generates_first_round_single_elim`).

**US3 (P2) — Resultado manual**:

5. **Red**: `test_match_routes.py::test_manual_result_marks_match_as_manual`.
6. **Green**: `match_service.register_manual_result()`.
7. **Red**: `test_manual_result_is_immutable` (intentar cambiar tag falla).
8. **Red**: `test_manual_result_advances_winner_in_single_elim`.
9. **Red**: `test_cannot_dispute_manual_result` (endpoint de disputa no existe → 404/405; documentado como "sin disputa" en contratos).

**US4 (P2) — Clasificación y cuadro**:

10. **Red**: `test_standings_service.py::test_points_one_per_win_zero_per_loss_byes_dont_count`.
11. **Red**: `test_tiebreak_head_to_head`.
12. **Red**: `test_circular_tie_breaks_by_inscription_date`.
13. **Red**: `test_inscription_date_same_breaks_by_participant_id` (edge case del spec).
14. **Red**: `test_tournament_routes.py::test_get_standings_reflects_confirmed_result`.
15. **Red**: `test_get_bracket_after_round_closure_generates_next_round`.

**US5 (P3) — Modificar antes de iniciar**:

16. **Red**: `test_rename_tournament_while_draft`, `test_change_format_while_open_registration`, `test_modify_after_start_rejected` (403/409).

**US6 (P3) — Cancelar torneo**:

17. **Red**: `test_cancel_from_in_progress`, `test_cancel_from_finalized_rejected`, `test_cancelled_is_read_only`.
18. **Red**: `test_cancel_notifies_all_participants` (verifica que se crean registros en `notifications`).

**Tests unitarios específicos** (fuera del flujo de rutas, dirigidos a la lógica pura):

- `test_calendar_service.py`:
  - `test_round_robin_N_even_pairs_everyone_once`.
  - `test_round_robin_N_odd_rotates_ghost_player_fairly` — propiedad: con `N` rondas impares, cada jugador real descansa **exactamente una vez**.
  - `test_single_elim_balances_bracket_with_byes_to_most_recent` — N=6: 2 byes, a los 2 inscritos más recientes.
  - `test_single_elim_next_round_not_generated_until_all_confirmed`.
- `test_standings_service.py` (ya listados arriba).
- `test_match_service.py`: validaciones defensivas (intentar registrar resultado en match de ronda futura → rechazo).

**Frontend**:

- `usePolling.test.js`: fake timers, `setInterval` llama cada 10 s, `clearInterval` en unmount.
- `TournamentDetail.test.jsx`: renderiza listado de participantes y botones según estado; mock via `msw` de `tournamentApi`.
- `MatchDetail.test.jsx`: organizador ve botón "Introducir resultado"; participante no organizador no lo ve.

**Regla invariante**: ningún commit introduce código productivo sin su test correspondiente en rojo antes. La primera tarea de cada bloque en `tasks.md` (Fase 2) será escribir el test que falla.

---

## § Algoritmo round-robin (rotación circular)

**Fuente**: método del círculo (*circle method*), descrito en la literatura estándar del problema del torneo round-robin. Referencias:
- Wikipedia — *Round-robin tournament § Scheduling algorithm*: https://en.wikipedia.org/wiki/Round-robin_tournament#Scheduling_algorithm (última revisión consultada: 2026-04-24).
- *Berger tables* (tablas Berger) — nomenclatura clásica en ajedrez.

### Descripción

Dados `N` participantes:
- Si `N` es par: `N-1` rondas, cada una con `N/2` enfrentamientos.
- Si `N` es impar: se añade un **jugador fantasma** (bye). Rondas = `N`, cada una con `(N-1)/2` enfrentamientos reales + 1 bye. El fantasma rota por todos los reales ⇒ cada real descansa exactamente una vez (propiedad **fairness-bye**).

### Implementación planeada (`services/calendar_service.py::generate_round_robin`)

```python
def generate_round_robin(participants: list[Participant]) -> list[Round]:
    n = len(participants)
    players = list(participants)
    if n % 2 == 1:
        players.append(None)          # jugador fantasma (bye)
        n += 1

    fixed = players[0]
    rotating = players[1:]
    total_rounds = n - 1
    rounds = []

    for r in range(total_rounds):
        round_matches = []
        round_players = [fixed] + rotating
        for i in range(n // 2):
            p1 = round_players[i]
            p2 = round_players[n - 1 - i]
            if p1 is None or p2 is None:
                # bye: el jugador no-None descansa esta ronda
                bye_player = p1 if p2 is None else p2
                round_matches.append(Match(player1=bye_player, player2=None, is_bye=True))
            else:
                round_matches.append(Match(player1=p1, player2=p2, is_bye=False))
        rounds.append(Round(number=r + 1, matches=round_matches))
        rotating = [rotating[-1]] + rotating[:-1]   # rota el último al frente

    return rounds
```

**Propiedades verificables por test**:
- *Completeness*: cada par `(pi, pj)` con `i ≠ j` aparece **exactamente una vez** en el conjunto de enfrentamientos.
- *Fairness-bye (N impar)*: cada participante real tiene exactamente un match `is_bye=True`.
- *Determinismo*: misma entrada (misma lista de participantes en el mismo orden) produce misma salida.

### Orden de los participantes en la entrada

Fijamos **orden de inscripción ascendente** (timestamp de aceptación; desempate por `participant.id`). Razón: el único orden estable y disponible en la fase de "iniciar" es el que los usuarios no pueden cambiar tras confirmar. Alternativa rechazada: `random.shuffle` — no reproducible ⇒ dificulta tests y auditoría.

---

## § Algoritmo eliminación directa (single elimination)

**Fuente**: problema clásico de bracket balanceado. Referencias:
- Wikipedia — *Single-elimination tournament § Seeding and byes*: https://en.wikipedia.org/wiki/Single-elimination_tournament (consultada 2026-04-24).

### Descripción

Dados `N` participantes:
- `bracket_size = smallest_power_of_two ≥ N`.
- `byes = bracket_size − N` ⇒ tantos participantes pasan directamente a la segunda ronda en la primera ronda.
- **Regla de asignación** (del prompt humano): los byes se asignan a los participantes con **inscripción más reciente** (mayor `accepted_at`).
- La **primera ronda** contiene sólo los matches de los participantes sin bye, emparejados en orden estable (inscripción ascendente, estándar de seeding). Los participantes con bye quedan pre-asignados a su posición en la segunda ronda.
- Rondas posteriores **no se generan** hasta cerrarse la ronda anterior (FR-027).

### Implementación planeada (`services/calendar_service.py::generate_single_elim_first_round`)

```python
def generate_single_elim_first_round(participants: list[Participant]) -> Round:
    n = len(participants)
    bracket_size = 1
    while bracket_size < n:
        bracket_size *= 2
    byes = bracket_size - n

    # participantes con bye: los de inscripción más reciente (accepted_at DESC)
    sorted_recent_first = sorted(participants, key=lambda p: p.accepted_at, reverse=True)
    bye_players = sorted_recent_first[:byes]
    playing = [p for p in participants if p not in bye_players]
    playing.sort(key=lambda p: p.accepted_at)

    matches = []
    for i in range(0, len(playing), 2):
        matches.append(Match(player1=playing[i], player2=playing[i + 1], is_bye=False))
    for bp in bye_players:
        matches.append(Match(player1=bp, player2=None, is_bye=True))

    return Round(number=1, matches=matches)
```

**Propiedades verificables por test** (SC-007):
- Si `N=6`: `bracket_size=8`, `byes=2`, primera ronda = 2 byes + 2 matches "reales" → 4 participantes sobreviven (2 bye + 2 ganadores) ⇒ segunda ronda es potencia de 2.
- Determinismo: misma lista, misma salida.

### Generación de rondas posteriores

`calendar_service.close_round_and_generate_next(round_id)` se dispara cuando el último match de la ronda se resuelve (en esta iteración, sólo por manual). Empareja los ganadores en orden posicional del bracket (ganador del match 1 vs ganador del match 2, etc.) y genera nuevos `tournament_code`s. Si sólo queda **un** participante tras la generación ⇒ transición del torneo a `finished` (FR-050).

---

## § Tournament code (en esta iteración)

**Decisión**: UUID v4 interno, no se consulta a la API de Riot.

**Justificación**:
- La spec bloquea la integración con Riot esta iteración. El requisito FR-031 ("código único restringido a los dos jugadores") se cumple a nivel del dominio: el backend asocia el UUID al par de participantes y rechaza reutilizaciones.
- La "restricción técnica en la plataforma de Riot" (que sólo los 2 jugadores puedan unirse a la sala con ese código) quedará activa cuando se cableé `HttpRiotAPIClient` en la iteración futura.
- `code_created_at` se persiste desde ya: sirve tanto a la validación temporal futura (FR-036c) como a auditoría interna.

**Fuente**: RFC 4122 (UUID).

---

## § Invitation expiry strategy

**Decisión**: verificación *on-read* (al listar y al intentar aceptar).

**Justificación**:
- Alternativa descartada: background worker con cron. Introduciría una dependencia nueva (APScheduler u otra) — incompatible con el stack fijado.
- Alternativa descartada: trigger de BBDD. Complica migraciones y debugging; viola Simplicity (Principio IV).
- La política *on-read* es suficiente: ningún endpoint acepta una invitación con `expires_at ≤ now()`. Las filas "expiradas" quedan en BBDD pero con `state='expired'` (se migra en el mismo request que descubre el vencimiento). No hay acumulación dañina: las invitaciones se listan con un filtro (`WHERE expires_at > now() OR state != 'pending'`).

**Trade-off aceptado**: si nadie vuelve a abrir la UI, la invitación permanece como `pending` en BBDD más allá de las 48 h. El efecto funcional es correcto (no puede aceptarse) y la limpieza física puede hacerse más tarde como tarea de mantenimiento.

---

## § Polling frontend (10 s)

**Decisión** (fijada por el prompt): `setInterval(fetch, 10000)` sobre endpoints:
- `GET /notifications?unread=true` — bandeja del usuario.
- `GET /tournaments/{id}` — refresca detalle (participantes, estado).
- `GET /tournaments/{id}/schedule` — rondas y matches.
- `GET /tournaments/{id}/standings` — tabla round-robin.

**Justificación de 10 s** (del prompt del humano; no cuestionable, Principio IV). Refuerza SC-003 (*<5 s* tras resultado): el peor caso de latencia percibida es ~10 s (una ventana de polling completa), lo cual es un **riesgo de incumplimiento** de SC-003 en el peor caso.

**Mitigación práctica**: tras acciones que el usuario ejecuta localmente (registrar resultado, cancelar torneo), el frontend dispara un *refresh inmediato* de la vista afectada sin esperar al siguiente tick; el polling cada 10 s cubre los cambios provenientes de otros usuarios. Documentado en `quickstart.md § Frontend patterns`.

**Fuentes**:
- React docs — *Effects with intervals*: https://react.dev/reference/react/useEffect.
- MDN — `setInterval` semantics: https://developer.mozilla.org/docs/Web/API/setInterval.

---

## § Dependencias diferidas

| Dependencia | Motivo de diferir | Criterio de reentrada |
|-------------|-------------------|-----------------------|
| `respx` (test-only) | Todavía ningún test exige mockear `httpx`. | Primer test que instancie `HttpRiotAPIClient`. |
| `HttpRiotAPIClient` (módulo productivo) | Bloqueado por la spec (vinculación Riot out-of-scope). | Cuando se reabra la integración con Riot. |
| Endpoint de verificación por API en `matches.py` | Lo mismo. | Lo mismo. |

---

## § Post-Design Re-check (tras Phase 1)

Evaluado después de redactar `data-model.md` y `contracts/*`:

- **Sin nuevas dependencias runtime** (se mantiene la lista de 001 + nada).
- **Sin endpoints que no tengan test planeado**.
- **Sin campos de entidad que no estén motivados por un FR o por una restricción del prompt**.
- El Protocol `RiotAPIClient` se define en código pero **no se inyecta** en ningún handler de 002: respeta "no código sin test" (Principio II) porque ningún handler lo consume.

**Constitution Check post-Phase 1**: **PASA sin observaciones**.
