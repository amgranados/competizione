# Phase 0 — Research: Añadir amigos

**Branch**: `004-add-friends` | **Date**: 2026-04-28
**Input**: [plan.md](./plan.md), [spec.md](./spec.md), `prompts/second/04-amigo.txt` (input histórico, Constitución V)

Este documento consolida las decisiones técnicas tomadas para resolver el plan, agrupadas por bloque. El stack está fijado por el humano (Constitución IV), por lo que esta sección **no evalúa alternativas de stack**: solo decisiones de cómo aplicar lo fijado.

---

## Scope

### Decisión

Se implementa la mecánica de amistad **completa a nivel API** (búsqueda, perfil ajeno, envío/aceptación/rechazo/eliminación, listado de solicitudes recibidas) y se cubre **a nivel UI** todo salvo el panel principal de solicitudes recibidas. El endpoint `GET /api/friends/requests` queda implementado y testeado pero sin un consumidor visual en esta iteración (lo declara explícitamente el prompt). El listado público "mis amigos" no es objeto de esta feature.

### Rationale

- El prompt fija textualmente la estructura del backend, los endpoints, el modelo de datos y la nota: "El endpoint GET /friends/requests existe y devuelve las solicitudes recibidas pendientes. No tiene UI asignada en esta fase." Constitución IV: el humano fija el cómo, no se cuestiona.
- La spec describe el flujo completo y deja FR-015 a FR-017 como cubrible con una UI futura del panel principal; documentar que el backend sí está listo permite que esa iteración consuma sin nuevas migraciones.

### Alternativas consideradas (rechazadas)

- **Implementar la UI del panel principal en esta fase**: rechazado por el prompt.
- **Implementar listado "mis amigos"**: rechazado. No exigido por spec ni prompt; añadiría endpoint y UI sin justificación inmediata.
- **Notificación in-app al recibir solicitud**: 002 ya tiene `notifications`; rechazado por el prompt y porque acoplaría features sin necesidad demostrada.

---

## HD-1: Estado de relación calculado en backend (no en frontend)

### Decisión

Cada respuesta relevante (`UserSearchResult`, `PublicProfileResponse`) incluye un campo `relationship_status` con uno de los cuatro valores: `SIN_RELACION`, `PENDIENTE_ENVIADA`, `PENDIENTE_RECIBIDA`, `AMIGO`. El frontend lo recibe ya calculado y solo lo usa para renderizar el `FriendshipButton`. **No existe** un endpoint independiente de tipo `GET /api/friends/status/{user_id}`.

### Rationale

- Lo dicta el prompt: "Los estados de relación posibles son: SIN_RELACION, PENDIENTE_ENVIADA, PENDIENTE_RECIBIDA, AMIGO. **El backend los calcula respecto al usuario autenticado en cada consulta.**"
- Centraliza la fuente de verdad en el backend: el frontend nunca tiene que mantener un caché de relaciones que pueda quedar inconsistente.
- Permite hacer la consulta con un único `LEFT JOIN` lateral por listado de búsqueda.

### Alternativas

- **Endpoint dedicado de estado**: rechazado. Multiplicaría peticiones al renderizar resultados de búsqueda (N+1 desde el cliente).
- **Estado calculado en frontend (con sus propios caches)**: rechazado. Repetiría lógica que ya vive en backend.

### Verificación testable

- `test_friends_service.py::test_compute_relationship_status_when_no_relation`
- `test_friends_service.py::test_compute_relationship_status_when_pending_sent`
- `test_friends_service.py::test_compute_relationship_status_when_pending_received`
- `test_friends_service.py::test_compute_relationship_status_when_accepted`
- `test_friends_routes.py::test_search_results_include_relationship_status_per_row`

---

## HD-2: Modelo de tabla `friendships` (una fila por relación)

### Decisión

Una sola tabla `friendships` con la forma:

```text
id              UUID PK
requester_id    UUID FK -> users.id  NOT NULL
addressee_id    UUID FK -> users.id  NOT NULL
status          ENUM('pending', 'accepted')  NOT NULL
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
```

**Constraints**:

- `UNIQUE (requester_id, addressee_id)` — impide duplicar la misma dirección.
- `CHECK (requester_id <> addressee_id)` — impide auto-amistad a nivel BD (defensa en profundidad sobre FR-014).
- Índices: `idx_friendships_requester (requester_id, status)` y `idx_friendships_addressee (addressee_id, status)` para hacer eficiente el cálculo de `relationship_status`.

**Semántica del status**:

- `pending` significa "solicitud direccional de `requester_id` a `addressee_id`": solo el `addressee_id` puede aceptar/rechazar.
- `accepted` significa "amistad bidireccional entre los dos"; los roles `requester`/`addressee` pierden relevancia funcional pero se preservan para trazabilidad.

**Aceptación**: la fila pasa de `pending` a `accepted` (UPDATE), no se crea una nueva.

**Rechazo**: la fila se borra (DELETE).

**Eliminación**: la fila `accepted` se borra (DELETE).

### Rationale

- La forma A↔B simétrica con dos filas espejo (`(A,B)` y `(B,A)`) obligaría a triggers o lógica replicada cada vez que se actualice el estado y a un constraint extra "ambas filas deben tener el mismo status" — más complejo sin beneficios funcionales.
- Una fila por relación deja la integridad referencial trivial: la única relación entre A y B es una sola tupla, y el cálculo del estado es un solo SELECT con un OR sobre las dos direcciones.
- El prompt deja libertad sobre la forma física exacta y solo exige `(id, requester_id, addressee_id, status, created_at)`.

### Alternativas

- **Filas espejo simétricas** (insertar `(A,B)` y `(B,A)` siempre): rechazado por las razones anteriores.
- **`status` con tres valores incluyendo `rejected`**: rechazado. Mantener filas rechazadas no aporta valor en esta feature (no hay analítica) y permite re-enviar una nueva solicitud sin choque de unicidad si se borra la rechazada (consistente con la asunción de la spec sobre re-envío).

### Verificación testable

- Migración Alembic incluye los tres constraints arriba.
- `test_friends_service.py::test_send_request_creates_pending_row`
- `test_friends_service.py::test_accept_request_updates_status_to_accepted`
- `test_friends_service.py::test_reject_request_deletes_row`
- `test_friends_service.py::test_remove_friend_deletes_accepted_row`
- `test_friends_routes.py::test_send_request_to_self_rejected_400`

---

## HD-3: Detección de duplicidad cruzada (race condition A↔B)

### Decisión

Antes de insertar una nueva fila `pending`, dentro de una transacción, se ejecuta:

```sql
SELECT id, status, requester_id, addressee_id
FROM friendships
WHERE (requester_id = :a AND addressee_id = :b)
   OR (requester_id = :b AND addressee_id = :a)
FOR UPDATE
```

(`:a` es `current_user.id`, `:b` es el `user_id` objetivo).

Lógica del servicio según el resultado:

| Caso | Acción |
|------|--------|
| 0 filas | INSERT (`requester_id=:a, addressee_id=:b, status='pending'`). Devolver `201 Created` con la fila. |
| 1 fila con `status='accepted'` | Devolver `409 Conflict`: "Ya sois amigos." |
| 1 fila con `status='pending'`, `requester_id=:a` | Devolver `409 Conflict`: "Ya tienes una solicitud pendiente con este usuario." |
| 1 fila con `status='pending'`, `requester_id=:b` | Devolver `409 Conflict`: "Este usuario ya te ha enviado una solicitud; acéptala desde tu panel." |

`FOR UPDATE` toma un row-level lock que persiste hasta el `COMMIT`/`ROLLBACK`. Combinado con `UNIQUE (requester_id, addressee_id)`, garantiza:

- Si A→B y B→A entran a la vez, una transacción bloquea las filas candidatas (vacío inicial), inserta `(A,B)` y commitea; la segunda transacción levanta el lock al ver `(A,B)` ya creado y devuelve `409` por la cuarta rama de la tabla anterior.
- Si dos peticiones idénticas A→B entran a la vez, una inserta y la otra levanta el `UniqueViolation` al hacer INSERT (defensa en profundidad: el `SELECT FOR UPDATE` detecta el caso, pero si la primera hubiera commiteado entremedias, el `UNIQUE` lo cazaría).

### Rationale

- El prompt exige "validado en backend" y la spec exige (FR-013, FR-021) que NO se puedan crear duplicados.
- `SELECT FOR UPDATE` es la forma estándar SQL de serializar inserciones condicionales sin acudir a niveles de aislamiento más altos (`SERIALIZABLE`).
- PostgreSQL con read-committed + `FOR UPDATE` es suficiente y mantiene throughput.

### Alternativas

- **Solo UNIQUE constraint**: rechazado. Resuelve A→B vs A→B pero no A→B vs B→A; uno de los dos quedaría como `pending` mientras el otro recibiría error confuso.
- **`SERIALIZABLE` global**: rechazado. Pesado y obliga a manejar `serialization_failure` con retry; el lock explícito es más predecible.
- **Triggers BD que normalicen siempre `requester_id < addressee_id`**: rechazado. Pierde la dirección de la solicitud (clave funcional para distinguir `PENDIENTE_ENVIADA` vs `PENDIENTE_RECIBIDA`).

### Verificación testable

- `test_friends_service.py::test_send_request_rejected_when_pending_in_other_direction`
- `test_friends_service.py::test_send_request_rejected_when_already_friends`
- `test_friends_service.py::test_send_request_rejected_when_pending_in_same_direction`
- `test_friends_routes.py::test_concurrent_cross_requests_only_one_succeeds` (simulado con dos calls secuenciales pero con asserts sobre 201 y 409 distinguibles).

---

## HD-4: Eliminación bidireccional

### Decisión

`DELETE /api/friends/{user_id}`:

```sql
DELETE FROM friendships
WHERE status = 'accepted'
  AND ( (requester_id = :a AND addressee_id = :b)
     OR (requester_id = :b AND addressee_id = :a) )
RETURNING id
```

(`:a` es `current_user.id`, `:b` es el `user_id` del path).

Si la consulta no afecta filas, devolver `404`. Si afecta una fila, devolver `204`.

### Rationale

- La fila única (HD-2) hace que un solo DELETE elimine la amistad simétricamente; no hay que tocar dos filas.
- El filtro `status = 'accepted'` evita que esto borre por error una solicitud `pending` (esa se elimina vía endpoints de aceptar/rechazar).

### Alternativas

- **Endpoint que reciba el `friendship_id`**: rechazado. La spec habla de "Eliminar amigo" desde el perfil del otro, donde el frontend tiene `user_id` pero no `friendship_id`. Usar `user_id` es más natural.
- **Marcar como "deleted" sin borrar**: rechazado. No hay valor histórico en la amistad después de cortarla y mantener filas inservibles solo crece la tabla.

### Verificación testable

- `test_friends_service.py::test_remove_friend_deletes_single_row_regardless_of_direction`
- `test_friends_service.py::test_remove_friend_404_when_no_accepted_friendship`
- `test_friends_service.py::test_remove_friend_does_not_delete_pending_request`
- `test_friends_routes.py::test_remove_friend_returns_204_then_search_shows_no_relation`

---

## HD-5: Usuarios anonimizados (interacción con 003)

### Decisión

- **Búsqueda**: el `SELECT` añade `WHERE deleted_at IS NULL` además de `WHERE id <> :current_user.id` y el `ILIKE`. Los anonimizados nunca aparecen.
- **`GET /api/profile/{nickname}`**: si el nickname pertenece a un usuario anonimizado (`deleted_at IS NOT NULL`), devolver `404` (igual que si el nickname no existiera).
- **`POST /api/friends/request/{user_id}`**: si el `user_id` apunta a un anonimizado, devolver `404`.
- **`POST /api/friends/request/{request_id}/accept|reject`**: si la solicitud existe pero el `requester` está anonimizado, devolver `404` ("solicitud ya no válida"). El sistema NO hace cleanup proactivo: la solicitud queda en BD pero los endpoints la filtran.
- **`DELETE /api/friends/{user_id}`**: si la otra parte está anonimizada, igualmente borra la fila (la amistad sigue siendo "real" en BD, y borrarla es lo correcto). Si el `user_id` ni siquiera existe en `users`, devuelve `404`.
- **`relationship_status` calculado**: si la otra parte está anonimizada y aparece por algún camino (no la búsqueda), devolver `SIN_RELACION` para evitar exponer la relación con un usuario "borrado". (En la práctica este camino no se da porque la búsqueda lo excluye y `GET /api/profile/{nickname}` también, pero queda como invariante.)

**Lo que NO hacemos**: limpieza proactiva al anonimizar un usuario. El plan de 003 anonimiza la fila `users` pero no toca `friendships`. En 004 se acepta esa decisión y se filtra con queries; sumar un cleanup en 003 retroactivamente está fuera de alcance.

### Rationale

- Mantiene la separación de responsabilidades entre 003 y 004: cada feature filtra lo suyo.
- Evita una migración cross-feature.
- Cero riesgo de exponer un nickname `deleted-XXXXXXXX` en una búsqueda o un perfil ajeno.

### Alternativas

- **Cleanup en cascada al anonimizar (modificar 003)**: rechazado. Reabre 003 sin necesidad demostrada; las filas huérfanas son invisibles y no rompen invariantes.
- **`ON DELETE CASCADE` sobre `friendships.user_id` apuntando a `users`**: NO ayuda aquí porque la anonimización NO borra la fila de `users` (es soft-delete).

### Verificación testable

- `test_friends_service.py::test_search_excludes_anonymized_users`
- `test_friends_routes.py::test_get_public_profile_404_for_anonymized_user`
- `test_friends_routes.py::test_send_request_to_anonymized_user_returns_404`
- `test_friends_routes.py::test_accept_request_when_requester_anonymized_returns_404`

---

## HD-6: Mínimo de longitud de búsqueda

### Decisión

`GET /api/friends/search?q=`:

- Si `q` no está presente o `len(q.strip()) == 0` → devolver `[]` (lista vacía) con `200`. **No es un error 400**: la spec dice "estado vacío informativo", no "error de validación".
- Si `len(q.strip()) >= 1` → ejecutar la búsqueda con `ILIKE '%' || strip(q) || '%'`, `LIMIT 20`.
- Sin máximo de longitud (Pydantic enforce `max_length=64` para evitar ataques con queries gigantes — coherente con la longitud máxima de nickname).

### Rationale

- El prompt exige `ILIKE %nickname%` y máximo 20 resultados, sin imponer un mínimo.
- Devolver `[]` ante consulta vacía sigue la asunción explícita de la spec.

### Alternativas

- **Mínimo 3 caracteres** (anti-DoS por queries muy cortas): rechazado por el prompt y por la spec (no se exige).
- **Devolver 400 ante consulta vacía**: rechazado; la UX espera que un input vacío no produzca error sino estado vacío.

### Verificación testable

- `test_friends_service.py::test_search_returns_empty_list_for_blank_query`
- `test_friends_service.py::test_search_is_case_insensitive`
- `test_friends_service.py::test_search_partial_match_inside_nickname`
- `test_friends_service.py::test_search_limited_to_20_results`
- `test_friends_service.py::test_search_excludes_self`

---

## HD-7: Política de errores HTTP

### Decisión

| Endpoint | Caso | Status | Body |
|---------|------|--------|------|
| `GET /api/friends/search` | Sin sesión | `401` | `{"detail": "No autenticado"}` |
| `GET /api/friends/search` | `q` vacía | `200` | `[]` |
| `POST /api/friends/request/{user_id}` | `user_id == current_user.id` | `400` | `{"detail": "No puedes enviarte una solicitud a ti mismo."}` |
| `POST /api/friends/request/{user_id}` | `user_id` no existe o anonimizado | `404` | `{"detail": "Usuario no encontrado."}` |
| `POST /api/friends/request/{user_id}` | Ya hay relación (cualquier dirección, pending o accepted) | `409` | `{"detail": "<mensaje específico de HD-3>"}` |
| `POST /api/friends/request/{user_id}` | OK | `201` | `FriendRequestResponse` |
| `POST /api/friends/request/{request_id}/accept` | `request_id` no existe o ya no en `pending` | `404` | `{"detail": "Solicitud no encontrada."}` |
| `POST /api/friends/request/{request_id}/accept` | `current_user` NO es `addressee_id` | `403` | `{"detail": "No puedes aceptar una solicitud que no es tuya."}` |
| `POST /api/friends/request/{request_id}/accept` | OK | `200` | `FriendRequestActionResult` |
| `POST /api/friends/request/{request_id}/reject` | Igual que accept con cambio "rechazar" | mismos status | mismos bodies |
| `DELETE /api/friends/{user_id}` | No hay amistad `accepted` con ese usuario | `404` | `{"detail": "No sois amigos."}` |
| `DELETE /api/friends/{user_id}` | OK | `204` | (sin body) |
| `GET /api/friends/requests` | Sin sesión | `401` | `{"detail": "No autenticado"}` |
| `GET /api/friends/requests` | OK | `200` | `list[FriendRequestResponse]` (puede ser `[]`) |

### Rationale

- Los códigos cumplen con el patrón establecido en 001/002/003 y son los estándar HTTP correctos.
- A diferencia de 003 con Riot, aquí no se enmascaran errores: no hay flujo con credenciales sensibles en el que distinguir un fallo concreto pueda comprometer al usuario.
- Mensajes en español para alinearse con el resto de mensajes del producto.

### Alternativas

- **`409` también para auto-solicitud**: rechazado. `400` es más correcto: el cliente envió un input lógicamente inválido, no hay conflicto de estado.
- **`403` cuando se manda solicitud a un usuario que ya es amigo**: rechazado. `409` (conflict) es lo correcto: la operación entra en conflicto con un recurso existente.
- **`401` indistinguible de `403`**: rechazado. La distinción es útil para el frontend (sin sesión → redirigir al login; sesión válida pero acción denegada → mostrar toast de error).

### Verificación testable

- `test_friends_routes.py` cubre cada fila con un caso al menos.

---

## TDD Workflow

Aplicación literal del Principio II (NO NEGOCIABLE).

### Orden de los ciclos Red → Green → Refactor

1. **Esquemas Pydantic v2** (`schemas/friends.py`): tests de serialización del enum `FriendshipStatus` y de `UserSearchResult` (test fallido → implementar mínimo).
2. **Modelo `Friendship`** (`models/friendship.py`): test de creación + `UNIQUE (requester_id, addressee_id)` + `CHECK (requester_id != addressee_id)`. La migración Alembic se implementa para hacer pasar el test de integración correspondiente.
3. **`friends_service.search_users`**: tests unitarios (exclusión del self, exclusión de anonimizados, ILIKE case-insensitive y parcial, límite 20, query vacía → `[]`).
4. **`friends_service.compute_relationship_status`**: tests unitarios de los cuatro estados.
5. **`friends_service.send_request`**: tests para los 4 caminos de HD-3 (200, 409 ya amigos, 409 pendiente misma dirección, 409 pendiente cruzada) más el 400 de auto-solicitud.
6. **`friends_service.accept_request`**: tests para 200, 404 (no existe), 404 (ya no pending), 403 (no eres addressee).
7. **`friends_service.reject_request`**: simétrico al anterior.
8. **`friends_service.remove_friend`**: tests para 204 (cualquier dirección), 404 (no hay amistad), 404 (solicitud pendiente, no amistad).
9. **`friends_service.list_received_requests`**: test trivial con fixture de varias solicitudes.
10. **Rutas FastAPI** (`api/routes/friends.py`): tests de integración con `httpx.AsyncClient`. Solo se cablean al main cuando los tests del servicio están verdes.
11. **Endpoint público de perfil** (`api/routes/profile.py::GET /api/profile/{nickname}`): test de integración (existe / no existe / anonimizado / sin sesión). Reutiliza la composición de 003 sin permitir mutaciones.
12. **Frontend**:
    - Unit (`FriendshipButton.test.jsx`): renderizado por estado (`SIN_RELACION`, `PENDIENTE_ENVIADA`, `PENDIENTE_RECIBIDA`, `AMIGO`).
    - Integración (`UserSearchBar.test.jsx`): debounced fetch a `/api/friends/search`, render del dropdown, navegación al hacer clic.
    - Integración (`UserProfile.test.jsx`): perfil ajeno con datos de LoL (mock MSW), pulsación del botón → transición de estado tras refetch.

### Estructura de fixtures (`conftest.py`)

Fixtures nuevos:

- `another_user` (usuario distinto al `authenticated_user` ya existente).
- `pending_request_a_to_b` (solicitud `pending` con `requester_id=alice`, `addressee_id=bob`).
- `accepted_friendship_a_b` (fila `accepted` entre `alice` y `bob`).
- `anonymized_user` (`User` con `deleted_at` no nulo y nickname `deleted-XXXXXXXX`, reutilizando la lógica de 003).

---

## Dependencies & CVE Audit

### Dependencias añadidas

| Paquete | Versión | Tipo | Motivo |
|---------|---------|------|--------|
| (ninguna) | — | — | El flujo es CRUD puro sobre tablas existentes + una nueva. Toda la infra (FastAPI, SQLAlchemy, Alembic, Pydantic, pytest, Vitest, MSW) ya está instalada desde 001/002/003. |

### Dependencias re-utilizadas (sin cambios)

`fastapi`, `sqlalchemy[asyncio]`, `alembic`, `asyncpg`, `aiosqlite`, `pydantic[email]`, `pydantic-settings`, `PyJWT`, `passlib[bcrypt]`, `bcrypt`, `python-multipart`, `slowapi`, `httpx`, `respx` (test-only, herencia 003), `pytest`, `pytest-asyncio`, `pytest-cov`. Frontend sin altas.

### CVE audit

> Constitución I obliga a auditar antes de instalar nuevas dependencias. **No se instalan dependencias nuevas en esta iteración**, por lo que no procede un nuevo audit; se reutilizan las versiones ya auditadas en 001/002/003. Si `/speckit.tasks` o `/speckit.implement` añadiera alguna por necesidad imprevista, debe levantarse un audit explícito antes de instalar.

---

## Riesgos identificados

| Riesgo | Mitigación |
|--------|------------|
| `ILIKE %q%` con un volumen grande de usuarios degrada en seq-scan | Aceptable en esta iteración (volumen estimado bajo). Si en producción se observa degradación, evaluar índice GIN trigram (`pg_trgm`) en una iteración posterior. No se introduce ahora porque el prompt no lo pide y `pg_trgm` es una extensión que requiere audit. |
| Solicitudes huérfanas tras anonimizar un usuario (003) | Filtrado en query (HD-5). El cleanup proactivo se descarta para no abrir 003. |
| Race condition A↔B simultánea creando dos solicitudes | `SELECT FOR UPDATE` + UNIQUE constraint (HD-3). |
| Frontend re-fetcheando demasiado en cada keystroke del buscador | `UserSearchBar.jsx` aplica debounce (300 ms). El backend además limita a 20 resultados, así que cada llamada es barata. |
| Bug visible: tras aceptar una solicitud, el botón en el resultado de búsqueda anterior queda como "Pendiente" en cliente | Cada vista relevante (`UserSearchBar`, `UserProfile`) refetch al abrirse o al volverse a foco. El estado nunca se cachea más allá del scope del componente. |
| Confusión de `request_id` vs `user_id` en frontend | Tipado claro en `friendsApi.js`: las funciones reciben el id correcto (`requestId` para accept/reject, `userId` para remove). Tests cubren las firmas. |

---

## Resultado

Phase 0 cierra **sin marcadores `NEEDS CLARIFICATION`**. Todas las preguntas que no resolvía la spec (forma física de la tabla, política contra duplicados cruzados, comportamiento ante anonimizados, política de errores HTTP, alcance del listado de solicitudes recibidas) se han fijado como decisiones humanas (HD-1 a HD-7), trazables y testeables.
