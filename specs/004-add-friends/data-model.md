# Phase 1 — Data Model: Añadir amigos

**Branch**: `004-add-friends` | **Date**: 2026-04-28
**Source**: derivado de [spec.md](./spec.md), constraints en [plan.md](./plan.md), decisiones en [research.md](./research.md).

Esta iteración **añade una entidad** y **no modifica** ninguna existente. Las entidades de 001 (`User`, `TokenBlacklist`), 002 (`Tournament`, `Participant`, `Invitation`, `Match`, `Notification`) y 003 (`RiotAccount` + columnas `users.avatar_url`, `users.deleted_at`) se mencionan solo en la medida en que sus invariantes participan en este modelo (lectura cruzada de `users.deleted_at` para filtros).

---

## Resumen

| Entidad | Tipo | Cambio en esta iteración |
|---------|------|--------------------------|
| `User` | sin cambios | Solo se consulta en lectura: la búsqueda filtra por `nickname ILIKE %q%`, excluye `id == current_user.id` y `deleted_at IS NOT NULL` |
| `Friendship` | **nueva** | Una fila por relación entre dos usuarios. Status `pending` o `accepted`. |
| `Tournament`, `Participant`, `Notification` | sin cambios | No participan en este modelo. |

---

## 1. `Friendship` (nueva)

Tabla nueva. Representa una solicitud de amistad pendiente o una amistad establecida entre dos usuarios.

```text
Table: friendships
```

| Campo | Tipo | Nullable | Default | Constraints |
|-------|------|----------|---------|-------------|
| `id` | `Uuid` | no | `uuid7()` | PK |
| `requester_id` | `Uuid` | no | — | FK → `users.id` ON DELETE CASCADE |
| `addressee_id` | `Uuid` | no | — | FK → `users.id` ON DELETE CASCADE |
| `status` | `Enum('pending', 'accepted')` | no | — | (definido como `friendship_status` ENUM en PostgreSQL) |
| `created_at` | `DateTime(timezone=True)` | no | `now()` | Timestamp del envío de la solicitud o de la última transición |

### Constraints

- `UNIQUE (requester_id, addressee_id)` — impide duplicar la misma dirección.
- `CHECK (requester_id <> addressee_id)` — defensa en profundidad sobre FR-014.
- Índices:
  - `idx_friendships_requester (requester_id, status)`
  - `idx_friendships_addressee (addressee_id, status)`
- ON DELETE CASCADE en ambas FK. Aunque la anonimización de 003 NO borra la fila de `users`, si en el futuro se hiciera hard-delete, las filas de `friendships` que apuntan al usuario eliminado se eliminan automáticamente.

### Reglas

- Al **crear** una solicitud (HD-3): dentro de una transacción, `SELECT ... FOR UPDATE` con OR sobre las dos direcciones. Si no hay fila → INSERT. Si hay fila `pending` o `accepted` → `409`.
- Al **aceptar**: `UPDATE friendships SET status='accepted' WHERE id=:request_id AND status='pending' AND addressee_id=:current_user_id RETURNING *`. Si afecta 0 filas → `404` (no existe, ya no pending) o `403` (no eres addressee — distinguible con un select previo o con un check explícito).
- Al **rechazar**: `DELETE FROM friendships WHERE id=:request_id AND status='pending' AND addressee_id=:current_user_id`. Si 0 filas → `404`/`403`.
- Al **eliminar amistad** (HD-4): `DELETE FROM friendships WHERE status='accepted' AND ((requester_id=:a AND addressee_id=:b) OR (requester_id=:b AND addressee_id=:a))`. Si 0 filas → `404`.
- Si el usuario referenciado por `requester_id` o `addressee_id` tiene `deleted_at` no nulo, las consultas de listas y de cómputo de estado lo filtran (HD-5). La fila sigue existiendo en BD; simplemente no se materializa en respuestas.

### Cálculo del `relationship_status` (HD-1)

Dado un par `(current_user_id, target_user_id)`:

```sql
SELECT requester_id, addressee_id, status
FROM friendships
WHERE (requester_id = :current_user_id AND addressee_id = :target_user_id)
   OR (requester_id = :target_user_id AND addressee_id = :current_user_id)
LIMIT 1;
```

Mapping del resultado:

| Fila encontrada | `relationship_status` |
|----------------|------------------------|
| Ninguna | `SIN_RELACION` |
| `status='accepted'` | `AMIGO` |
| `status='pending'` y `requester_id == current_user_id` | `PENDIENTE_ENVIADA` |
| `status='pending'` y `requester_id == target_user_id` | `PENDIENTE_RECIBIDA` |

Para listas (resultados de búsqueda con N usuarios), se hace una sola consulta cruzada con `IN (:user_ids)` y se mapea por usuario en memoria, evitando N+1.

---

## 2. DTOs y enum

Definidos en `schemas/friends.py`. No se persisten; viajan por la API.

### `FriendshipStatus` (enum)

```text
SIN_RELACION
PENDIENTE_ENVIADA
PENDIENTE_RECIBIDA
AMIGO
```

### `UserSearchResult`

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | `UUID` | |
| `nickname` | `str` | |
| `avatar_url` | `HttpUrl \| None` | Heredado de 003 |
| `relationship_status` | `FriendshipStatus` | Calculado en backend |

### `FriendRequestResponse`

(Devuelta tras `POST /api/friends/request/{user_id}` y por `GET /api/friends/requests`.)

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | `UUID` | El `friendship_id` (PK de la fila) |
| `requester_id` | `UUID` | |
| `addressee_id` | `UUID` | |
| `requester_nickname` | `str` | Conveniencia para el panel principal |
| `requester_avatar_url` | `HttpUrl \| None` | |
| `created_at` | `datetime` | UTC |

### `FriendRequestActionResult`

(Devuelta tras aceptar o rechazar.)

| Campo | Tipo | Notas |
|-------|------|-------|
| `request_id` | `UUID` | |
| `action` | `Literal["accepted", "rejected"]` | |
| `relationship_status` | `FriendshipStatus` | El nuevo estado entre el `current_user` y el `requester` original (`AMIGO` si accept; `SIN_RELACION` si reject). |

### `PublicProfileResponse`

(Devuelta por `GET /api/profile/{nickname}`. Variante "público" del perfil del propio usuario; reutiliza la composición de 003 sin email ni controles de edición.)

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | `UUID` | |
| `nickname` | `str` | |
| `avatar_url` | `HttpUrl \| None` | |
| `linked_games` | `list[LinkedGameSummary]` | Heredado de 003 |
| `lol_stats` | `LoLStatsResponse \| None` | Heredado de 003; presente solo si hay LoL vinculado |
| `relationship_status` | `FriendshipStatus` | Calculado vs el `current_user` |

**No incluye** `email` (no es información pública) ni los flags/controles de edición. El frontend distingue "perfil propio" de "perfil ajeno" por la URL (`/profile` vs `/users/:nickname`) y por la presencia/ausencia de `relationship_status`.

---

## 3. Estados y transiciones de `Friendship`

```text
                           POST /friends/request/{addressee_id}
                                      |
                                      v
            +-------------------+
            |    no_existe      |   (sin fila)
            +-------------------+
                      |
                      | INSERT (requester=A, addressee=B, status=pending)
                      v
            +-------------------+
            |     pending       |  -- POST /friends/request/{id}/accept (por B) -->  +-------------------+
            +-------------------+                                                    |     accepted      |
                      |                                                              +-------------------+
                      | POST /friends/request/{id}/reject (por B)                              |
                      v                                                                        | DELETE /friends/{user_id}
            +-------------------+                                                              v
            |    no_existe      |  <----------------------------------------------- +-------------------+
            +-------------------+                                                   |    no_existe      |
                                                                                    +-------------------+
```

Solo el `addressee_id` puede aceptar/rechazar (controlado en backend). Cualquiera de los dos puede pulsar "Eliminar amigo" sobre una amistad `accepted`.

No hay estado intermedio "rechazada persistida": el rechazo borra la fila para que el remitente pueda volver a enviar otra solicitud más adelante (consistente con la asunción de la spec sobre re-envío).

---

## 4. Estados de `User` relevantes a esta feature

```text
        +---------+    DELETE /api/profile/me     +-------------+
        | activo  | ----------------------------> | anonimizado |
        +---------+   (003)                       +-------------+
            |
            |  visible en búsqueda y como destino de solicitudes
            v
        (resto del flujo de amigos)
```

Una vez `deleted_at` está presente, el usuario:

- NO aparece en `GET /api/friends/search`.
- NO es accesible vía `GET /api/profile/{nickname}` (404).
- NO se puede recibir solicitudes (`POST /api/friends/request/{user_id}` → 404).
- NO se puede aceptar una solicitud cuyo remitente está anonimizado (404 — consistente con HD-5).

Las filas en `friendships` que lo referencian quedan en BD pero invisibles a través de los endpoints de 004. El cleanup proactivo está fuera de alcance.

---

## 5. Migración Alembic prevista

Migración nueva `add_friendships.py`:

1. `CREATE TYPE friendship_status AS ENUM ('pending', 'accepted');`
2. `CREATE TABLE friendships (...)` con las columnas y constraints anteriores; índices `idx_friendships_requester` y `idx_friendships_addressee`.
3. Sin backfill: tabla vacía al inicio.

`downgrade()`:

1. `DROP TABLE friendships;`
2. `DROP TYPE friendship_status;`

---

## 6. Invariantes globales (testeables)

| ID | Invariante | Test que la valida |
|----|-----------|--------------------|
| INV-1 | `UNIQUE (requester_id, addressee_id)` impide duplicar la misma dirección | `test_friendship_unique_per_direction` |
| INV-2 | `CHECK (requester_id <> addressee_id)` impide auto-amistad a nivel BD | `test_friendship_check_no_self_link` |
| INV-3 | El cómputo de `relationship_status` es determinista para cualquier par `(a,b)` | `test_compute_relationship_status_*` (4 tests) |
| INV-4 | `DELETE FROM friendships WHERE status='accepted' AND ...` es simétrico (borra la única fila independientemente de quién hizo la petición original) | `test_remove_friend_deletes_single_row_regardless_of_direction` |
| INV-5 | `POST /api/friends/request/{user_id}` con `user_id == current_user.id` → 400 | `test_send_request_to_self_rejected_400` |
| INV-6 | Tras `accept`, la fila pasa de `pending` a `accepted` (UPDATE, no INSERT) | `test_accept_request_updates_status_to_accepted` |
| INV-7 | Tras `reject`, la fila se borra (DELETE) | `test_reject_request_deletes_row` |
| INV-8 | Solo el `addressee_id` puede aceptar/rechazar; el `requester_id` recibe 403 | `test_accept_request_forbidden_for_non_addressee` |
| INV-9 | Búsqueda excluye al `current_user` y a usuarios con `deleted_at IS NOT NULL` | `test_search_excludes_self`, `test_search_excludes_anonymized_users` |
| INV-10 | Búsqueda case-insensitive y por coincidencia parcial | `test_search_is_case_insensitive`, `test_search_partial_match_inside_nickname` |
| INV-11 | Búsqueda devuelve máximo 20 resultados | `test_search_limited_to_20_results` |
| INV-12 | Solicitudes A→B y B→A simultáneas: solo una crea fila; la otra recibe 409 | `test_concurrent_cross_requests_only_one_succeeds` |

---

## Notas finales

- No hay cambios en `User`, `RiotAccount`, `Tournament`, `Participant`, `Invitation`, `Match`, `Notification` ni `TokenBlacklist`. La feature solo **lee** `users` (búsqueda y resolución de nickname) y **no** modifica la integridad histórica de torneos.
- El "panel principal con UI de solicitudes recibidas" no se construye en esta iteración. `GET /api/friends/requests` queda implementado y testeado para que la futura iteración del panel solo tenga que consumirlo.
