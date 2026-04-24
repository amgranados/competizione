# Phase 1 — Data Model: Tournament Management

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md)

Entidades y reglas de validación derivadas de la spec y del stack fijado en `prompts/second/02-torneo.txt`. Los tipos se expresan a nivel de dominio; el mapeo concreto a columnas SQLAlchemy ocurrirá durante la implementación (siempre vía TDD, Principio II).

---

## Enums (tipos cerrados)

```
TournamentFormat   = "round_robin" | "single_elim"
TournamentState    = "draft" | "open" | "active" | "finished" | "cancelled"
InvitationState    = "pending" | "accepted" | "rejected" | "expired" | "cancelled"
MatchState         = "pending" | "manual"
                     # "verified_api" se reserva pero NO se acepta aún (scope 002)
NotificationType   = "invitation_received" | "invitation_cancelled"
                   | "invitation_accepted" | "invitation_rejected"
                   | "tournament_started" | "tournament_cancelled"
                   | "match_generated" | "match_resolved"
                   | "tournament_finished"
```

---

## Entidad: `Tournament`

Fuente: spec §Key Entities "Torneo"; prompt (IDs UUID v4).

| Campo | Tipo | Restricciones | Origen |
|-------|------|---------------|--------|
| `id` | UUID v4 | PK. | Prompt. |
| `name` | string | No nulo, 1–100 chars (trimmed). | Spec FR-005, FR-021. |
| `start_at` | timestamp (UTC) nullable | Orientativa. Puede ser `null` si el organizador no la fijó. | Spec FR-005, FR-008. |
| `format` | `TournamentFormat` | No nulo; inmutable tras `active`. | Spec FR-005, FR-019, FR-030. |
| `state` | `TournamentState` | No nulo, default `"draft"` al crear. | Spec FR-007, FR-016…FR-020, FR-055, FR-056. |
| `organizer_id` | UUID v4 | FK → `User.id`, indexado, no nulo. | Spec FR-006. |
| `created_at` | timestamp (UTC) | No nulo, default `now()`. | Estándar. |
| `started_at` | timestamp (UTC) nullable | Se fija al transitar a `active`. | Spec FR-018. |
| `finished_at` | timestamp (UTC) nullable | Se fija al transitar a `finished` (o por cancelación). | Spec FR-020, FR-050. |
| `cancelled_at` | timestamp (UTC) nullable | Se fija al transitar a `cancelled`. | Spec FR-055. |

### Reglas de validación

- `name`: `len(name.strip()) ∈ [1, 100]`.
- `start_at`: si se envía, es `datetime` con timezone. No se valida "mayor que ahora" (la spec lo considera orientativo).
- `format`: sólo modificable en estados `draft` o `open` (FR-021).
- `state`: transiciones aceptadas (ver diagrama `contracts/tournament-lifecycle.puml`):
  - `draft → open` (FR-017, acción explícita del organizador).
  - `draft → cancelled` (FR-055).
  - `open → active` (FR-018, ≥2 participantes confirmados).
  - `open → cancelled`.
  - `active → finished` (automático al confirmarse el último resultado pendiente — FR-020, FR-050).
  - `active → cancelled`.
  - `finished` y `cancelled` son **terminales** (FR-056).

### Autorización

- Crear: cualquier usuario autenticado (FR-005).
- Leer detalle: `organizer_id` o cualquier `Participant.user_id` del torneo o cualquier `Invitation.invited_user_id` pendiente. Otros usuarios no ven el torneo.
- Modificar (nombre, fecha, formato): sólo `organizer_id` y sólo en `draft` u `open` (FR-021, FR-022).
- Iniciar / cancelar: sólo `organizer_id`.

---

## Entidad: `Participant`

Fuente: spec §Key Entities "Participante"; prompt.

| Campo | Tipo | Restricciones | Origen |
|-------|------|---------------|--------|
| `id` | UUID v4 | PK. | Prompt. |
| `tournament_id` | UUID v4 | FK → `Tournament.id`, indexado, no nulo. | — |
| `user_id` | UUID v4 | FK → `User.id`, no nulo. | Spec. |
| `accepted_at` | timestamp (UTC) | No nulo. Se fija al aceptar la invitación (o al inscribir al organizador en sí mismo, si se añade como participante). | Spec FR-047/FR-048 (desempate). |
| `removed` | bool | Default `false`. Baja lógica (se marca al retirar del torneo pre-inicio). | Spec FR-015. |

### Unicidad e integridad

- `UNIQUE (tournament_id, user_id)`: un usuario no aparece dos veces en el mismo torneo.
- Tras `tournament.state = 'active'`: inserciones/eliminaciones bloqueadas por la capa de servicio (FR-019, FR-022).
- Un usuario **puede** ser participante en múltiples torneos simultáneamente (spec Assumption).

### Reglas derivadas

- **Orden de inscripción** (usado para tie-break y seeding) = `accepted_at ASC, id ASC` (orden estable, determinista).

---

## Entidad: `Invitation`

Fuente: spec §Key Entities "Invitación a torneo".

| Campo | Tipo | Restricciones | Origen |
|-------|------|---------------|--------|
| `id` | UUID v4 | PK. | Prompt. |
| `tournament_id` | UUID v4 | FK → `Tournament.id`, indexado, no nulo. | — |
| `invited_user_id` | UUID v4 | FK → `User.id`, no nulo. | Spec FR-009. |
| `inviter_user_id` | UUID v4 | FK → `User.id`, no nulo. En esta iteración = `tournament.organizer_id` (registrado para futura delegación). | Spec FR-009. |
| `state` | `InvitationState` | No nulo, default `"pending"`. | Spec FR-012 / FR-013 / FR-014. |
| `created_at` | timestamp (UTC) | No nulo, default `now()`. | — |
| `expires_at` | timestamp (UTC) | No nulo; `= created_at + 48h`. | Spec FR-013. |
| `responded_at` | timestamp (UTC) nullable | Se fija al aceptar/rechazar/cancelar/expirar. | — |

### Unicidad

- `UNIQUE (tournament_id, invited_user_id)` **parcial** sobre `state = 'pending'`: se permite reinvitar a alguien cuya invitación previa fue rechazada/expirada/cancelada, pero no duplicar una pendiente.
- No se puede invitar a un usuario que ya sea `Participant` del torneo: validado por servicio.

### Reglas de estado (ver diagrama `contracts/tournament-lifecycle.puml`, subsección Invitation)

- `pending → accepted`: crea `Participant` con `accepted_at = now()`. Requiere `tournament.state ∈ {draft, open}` y `now < expires_at`.
- `pending → rejected`: por el invitado. Requiere `now < expires_at`.
- `pending → cancelled`: por el organizador. Requiere `now < expires_at`.
- `pending → expired`: se materializa al leer (check-on-read) cuando `now ≥ expires_at` y `state = pending` (ver research.md § Invitation expiry).

### Autorización

- Crear: `organizer_id` del torneo, sobre torneo en `draft` u `open`.
- Ver sus invitaciones: `invited_user_id`.
- Ver las invitaciones del torneo: `organizer_id`.
- Aceptar / rechazar: `invited_user_id`.
- Cancelar: `organizer_id`.

### Nota sobre FR-010 (diferida)

En esta iteración no se verifica que `invited_user` tenga cuenta de LoL vinculada (ver `plan.md § Scope`). Se añadirá una validación cuando exista la entidad `RiotAccount`.

### Nota sobre HD-1 (sistema de amistades) — resuelta

Decisión humana 2026-04-24 (ver `research.md § HD-1`): la invitación se acepta sobre **cualquier `User`** registrado sin comprobar relación de amistad. El check de amistad se reintroducirá como filtro previo en `tournament_service.invite()` cuando exista el servicio de amistades.

---

## Entidad: `Match` (Enfrentamiento)

Fuente: spec §Key Entities "Enfrentamiento" y "Código de sala"; prompt.

Un `Match` cubre tanto un enfrentamiento jugable como un **bye** (enfrentamiento sin oponente). Los byes se modelan aquí para que la clasificación y el cuadro puedan inspeccionar la misma estructura.

| Campo | Tipo | Restricciones | Origen |
|-------|------|---------------|--------|
| `id` | UUID v4 | PK. | Prompt. |
| `tournament_id` | UUID v4 | FK → `Tournament.id`, indexado, no nulo. | — |
| `round_number` | int | ≥ 1. | Spec. |
| `bracket_position` | int nullable | Posición dentro de la ronda (seeding en eliminación directa). `null` en round-robin. | Prompt (necesario para avance automático en eliminación directa). |
| `player1_id` | UUID v4 | FK → `Participant.id`, no nulo. | — |
| `player2_id` | UUID v4 nullable | FK → `Participant.id`. `null` ⇔ es un bye. | Spec (byes). |
| `is_bye` | bool | `true` si `player2_id IS NULL`. Columna redundante para queries rápidas. | — |
| `tournament_code` | string (UUID v4) nullable | No nulo si `is_bye = false`. `null` en byes (FR-048 / prompt: los byes no generan código). | Spec FR-031, FR-048 + prompt. |
| `code_created_at` | timestamp (UTC) nullable | Se fija junto con `tournament_code`. Usado por la futura validación temporal (FR-036c). | Spec FR-033. |
| `state` | `MatchState` | No nulo. `pending` inicial. `manual` al registrarse resultado (esta iteración). En un bye: `pending` al crear; al cerrarse la ronda, transita a `manual` con `winner_participant_id = player1_id` (el bye "avanza" al único jugador). | Spec FR-041, FR-042. |
| `winner_participant_id` | UUID v4 nullable | FK → `Participant.id`, ∈ {`player1_id`, `player2_id`} si no es bye; = `player1_id` si es bye resuelto. | Spec FR-040, FR-050. |
| `resolved_at` | timestamp (UTC) nullable | Se fija al registrar resultado manual o al resolver un bye. | — |

### Reglas de validación e integridad

- `player1_id ≠ player2_id` (cuando `player2_id ≠ null`).
- `(tournament_id, round_number, bracket_position)` **único** en eliminación directa.
- En round-robin, el conjunto de matches de un torneo cumple: cada par `{p_i, p_j}` aparece en **exactamente un** match no-bye.
- `state = 'manual'` es **inmutable** (FR-042). La capa de servicio rechaza cualquier UPDATE que intente cambiarlo; la ruta no expone método para ello.
- `winner_participant_id` se fija **sólo** al transitar `pending → manual`, nunca se reescribe.
- Los byes (`is_bye = true`) **no suman puntos** al calcular la clasificación (FR-048, prompt).
- Los byes **no generan** `tournament_code` (prompt).

### Transiciones de estado

```
[pending] --register_manual_result--> [manual]           # US3
[pending]  (bye auto-resuelve al cerrarse la ronda en single-elim)
           --resolve_bye--> [manual]                     # winner = player1; tag permanente

# "verified_api" queda reservado como valor del enum; el servicio no acepta transiciones a él en esta iteración.
```

### Autorización

- Lectura del match (incluido `tournament_code`): `player1.user_id`, `player2.user_id`, `tournament.organizer_id`. Otros usuarios: campo `tournament_code` elidido del payload.
- Registrar resultado manual: **sólo** `tournament.organizer_id` (spec FR-040 explícita).
- Disputa: **no existe endpoint** (FR-044).

---

## Entidad: `Notification`

Fuente: spec FR-011, FR-057; prompt ("notificaciones cada 10 s"). La spec no detalla la entidad; se dimensiona mínima para el polling.

| Campo | Tipo | Restricciones | Origen |
|-------|------|---------------|--------|
| `id` | UUID v4 | PK. | Prompt. |
| `user_id` | UUID v4 | FK → `User.id`, indexado, no nulo. | — |
| `type` | `NotificationType` | No nulo. | Diseño. |
| `tournament_id` | UUID v4 nullable | FK → `Tournament.id` (soft: sin cascade para preservar historial). | — |
| `match_id` | UUID v4 nullable | FK → `Match.id`. | — |
| `invitation_id` | UUID v4 nullable | FK → `Invitation.id`. | — |
| `created_at` | timestamp (UTC) | No nulo, default `now()`. | — |
| `read_at` | timestamp (UTC) nullable | Se fija al marcar leída. | — |

### Reglas de uso

- **Una notificación por evento por usuario**: al cancelar un torneo con 5 participantes se insertan 5 filas (una por participante).
- El endpoint `GET /notifications?unread=true` devuelve las del usuario autenticado con `read_at IS NULL`, ordenadas por `created_at DESC`. Polling cada 10 s.
- `PATCH /notifications/{id}/read` marca `read_at = now()`.
- No se expone endpoint de borrado en esta iteración (retención completa para auditoría).

### Eventos que generan notificaciones (mapeo)

| Evento | Destinatarios | `type` |
|--------|---------------|--------|
| Organizador invita a un usuario | Invitado | `invitation_received` |
| Organizador cancela invitación | Invitado | `invitation_cancelled` |
| Invitado acepta | Organizador | `invitation_accepted` |
| Invitado rechaza | Organizador | `invitation_rejected` |
| Organizador inicia torneo | Todos los participantes | `tournament_started` |
| Organizador cancela torneo | Todos los participantes | `tournament_cancelled` |
| Sistema genera match (incluye nueva ronda de single-elim) | Los 2 jugadores (no aplica a byes) | `match_generated` |
| Organizador registra resultado manual | Los 2 jugadores | `match_resolved` |
| Sistema finaliza torneo | Todos los participantes | `tournament_finished` |

---

## Entidad derivada (no persistida): `Round`

No es una tabla; es una **agrupación lógica** dada por `Match.round_number` dentro de un `tournament_id`. El servicio `calendar_service` devuelve `Round` como dataclass durante la generación. El estado "ronda completada" se calcula:

```python
round_completed = all(m.state != 'pending' for m in matches if not m.is_bye) \
               and all(m.state == 'manual' for m in matches if m.is_bye)
```

**Transición clave** (eliminación directa): al cumplirse la condición anterior para la ronda actual y si el torneo no está en su gran final, se generan los matches de la ronda `n+1` y sus códigos (FR-028).

---

## Entidad derivada (no persistida): `StandingEntry` (clasificación round-robin)

Calculada **a demanda** por `standings_service.compute(tournament)`. No hay tabla: recalcular de cero tras un resultado es barato en el tamaño esperado (≤32 participantes, ≤496 matches).

Campos devueltos:

| Campo | Tipo | Cálculo |
|-------|------|---------|
| `participant_id` | UUID v4 | — |
| `user_id` | UUID v4 | — |
| `wins` | int | `count(matches where winner_participant_id = participant_id AND is_bye = false)` |
| `losses` | int | `count(matches where winner in {p1,p2}\{participant} AND participant is p1 or p2 AND state = 'manual')` |
| `byes` | int | `count(matches where is_bye = true AND player1_id = participant_id)` (byes del participante). |
| `points` | int | `= wins` (FR-048: 1 pt/victoria, 0/derrota, byes no puntúan). |
| `rank` | int | Posición tras aplicar el algoritmo de ordenación (abajo). |

### Algoritmo de ordenación (FR-048)

1. Por **`points` DESC**.
2. En caso de empate entre dos: resultado del **enfrentamiento directo** entre ambos (`winner_participant_id`).
3. En caso de empate circular (tres o más con dependencia cíclica en directos): **`accepted_at` ASC** (el más antiguo arriba).
4. **Desempate final estable** (edge case spec): `participant.id` ASC.

Implementación: DAG de "A vence a B" sobre los empatados en puntos; detección de ciclo con DFS; fallback al paso 3 sólo cuando el grafo es cíclico.

**Fuente de las reglas**: spec §Key Entities + FR-048 + edge case en la spec ("fecha de inscripción idéntica ⇒ id del participante").

---

## Diagrama ER simplificado (PlantUML)

Ver `contracts/tournament-lifecycle.puml` para el diagrama de estados. El ER es directo y no se diagrama aparte; la referencia canónica son las tablas de arriba.

```
User (001)  1 ──< organizer_id ── * Tournament
User (001)  1 ──< user_id     ── * Participant
User (001)  1 ──< invited_user_id ── * Invitation
Tournament  1 ──< tournament_id ── * Participant
Tournament  1 ──< tournament_id ── * Invitation
Tournament  1 ──< tournament_id ── * Match
Participant 1 ──< player1_id   ── * Match
Participant 1 ──< player2_id   ── * Match  (nullable en byes)
Participant 1 ──< winner_participant_id ── * Match
User (001)  1 ──< user_id ── * Notification
```

---

## Autorización — resumen transversal

Todos los endpoints de 002 exigen autenticación vía la cookie de access JWT (herencia 001). Además:

| Endpoint (grupo) | Regla |
|------------------|-------|
| `POST /tournaments` | Autenticado. |
| `GET /tournaments/{id}` | Organizador, participante, o invitado (pendiente). |
| `PATCH /tournaments/{id}` | Organizador, y torneo ∈ {draft, open}. |
| `POST /tournaments/{id}/open` | Organizador, torneo = draft. |
| `POST /tournaments/{id}/start` | Organizador, torneo = open, ≥2 participantes. |
| `POST /tournaments/{id}/cancel` | Organizador, torneo ∉ {finished, cancelled}. |
| `POST /tournaments/{id}/invitations` | Organizador, torneo ∈ {draft, open}. |
| `POST /tournaments/{id}/invitations/{iid}/cancel` | Organizador, invitación pendiente y no expirada. |
| `POST /invitations/{iid}/accept|reject` | Usuario = `invited_user_id`, invitación pendiente y no expirada. |
| `DELETE /tournaments/{id}/participants/{pid}` | Organizador, torneo ∈ {draft, open}. |
| `GET /tournaments/{id}/schedule` | Organizador o participante. |
| `GET /tournaments/{id}/standings` | Organizador o participante (sólo round-robin). |
| `GET /tournaments/{id}/bracket` | Organizador o participante (sólo single-elim). |
| `GET /matches/{id}` | Organizador o los 2 jugadores; el campo `tournament_code` se elide para terceros autorizados que no estén en `{player1, player2, organizer}`. |
| `POST /matches/{id}/manual-result` | Organizador. |
| `GET /notifications` / `PATCH /notifications/{id}/read` | Usuario dueño. |

Rechazo estándar: `401` si no autenticado, `403` si autenticado pero sin permiso, `404` si el recurso no existe **o** el usuario no tiene permiso para verlo (para no filtrar existencia — patrón OWASP).
