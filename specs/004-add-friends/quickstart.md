# Quickstart — 004-add-friends

**Branch**: `004-add-friends` | **Date**: 2026-04-28
**Stack input (humano)**: `prompts/second/04-amigo.txt` (Constitución V — input histórico).

Este documento sirve como guía operativa para arrancar la feature en local, ejecutar el flujo TDD y comprobar manualmente los flujos clave de búsqueda, perfil ajeno y gestión de amistad.

---

## 1. Variables de entorno

`backend/.env` (ver `backend/.env.example`):

```env
DATABASE_URL=postgresql+asyncpg://competizione:competizione@localhost:5432/competizione
SECRET_KEY=<32+ chars random>
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
FRONTEND_ORIGIN=http://localhost:5173
COOKIES_SECURE=false               # true en producción/HTTPS
RIOT_API_KEY=<heredada de 003; opcional para esta iteración>
```

> Esta iteración **no introduce nuevas variables de entorno**. Si `RIOT_API_KEY` no está definida, el `MockRiotAPIClient` heredado de 003 sigue funcionando para el bloque LoL del perfil ajeno.

`frontend/.env` (sin variables nuevas en esta iteración).

---

## 2. Instalación

```bash
# Backend
cd backend
python -m venv .venv
. .venv/Scripts/activate          # Windows / bash
pip install -r requirements.txt   # sin altas en 004

# Migraciones
alembic upgrade head              # aplica add_friendships

# Frontend
cd ../frontend
npm install                       # sin altas en 004
```

---

## 3. Arranque

```bash
# Backend
cd backend
uvicorn app.main:app --reload --port 8000

# Frontend (otra terminal)
cd frontend
npm run dev                        # abre http://localhost:5173
```

Rutas relevantes en el frontend:

- `/login`, `/register` — heredadas de 001.
- `/dashboard`, `/tournaments/:id`, `/matches/:id` — heredadas de 002.
- `/profile` — heredada de 003 (perfil propio).
- **`/users/:nickname`** — nueva en 004 (perfil de otro usuario).
- **`UserSearchBar`** se monta en el header global (decisión visual no contractual; se ajusta sin tocar la API).

---

## 4. Flujo TDD recomendado

Aplicación literal del Principio II. Empezar siempre por un test fallido. Comandos:

```bash
# Backend (todos los tests)
cd backend
pytest

# Solo unit
pytest tests/unit -q

# Solo el archivo en el que estás
pytest tests/unit/test_friends_service.py::test_search_excludes_self -q
```

```bash
# Frontend
cd frontend
npm run test                       # interactivo
npm run test:run                   # one-shot CI-mode
npm run test:coverage
```

### Orden sugerido de Red → Green → Refactor

1. `tests/unit/test_friends_service.py::test_search_*`
   - `test_search_returns_empty_list_for_blank_query`
   - `test_search_is_case_insensitive`
   - `test_search_partial_match_inside_nickname`
   - `test_search_limited_to_20_results`
   - `test_search_excludes_self`
   - `test_search_excludes_anonymized_users`
2. `tests/unit/test_friends_service.py::test_compute_relationship_status_*` (4 estados).
3. `tests/unit/test_friends_service.py::test_send_request_*`
   - `test_send_request_creates_pending_row`
   - `test_send_request_to_self_rejected_400`
   - `test_send_request_rejected_when_already_friends`
   - `test_send_request_rejected_when_pending_in_same_direction`
   - `test_send_request_rejected_when_pending_in_other_direction`
4. `tests/unit/test_friends_service.py::test_accept_request_*` y `test_reject_request_*`.
5. `tests/unit/test_friends_service.py::test_remove_friend_*` (incluye bidireccionalidad y aislamiento de pendientes).
6. `tests/unit/test_friends_service.py::test_list_received_requests_*`.
7. `tests/integration/test_friends_routes.py` — cablea endpoints; cada test exige una ruta concreta y se hace pasar implementándola.
8. `tests/integration/test_profile_routes.py::test_get_public_profile_*` — añade los casos del perfil ajeno.
9. Frontend:
   - `tests/unit/FriendshipButton.test.jsx` (cuatro estados).
   - `tests/integration/UserSearchBar.test.jsx` (debounced fetch + render dropdown + navegación al clic).
   - `tests/integration/UserProfile.test.jsx` (perfil ajeno con FriendshipButton funcional; transiciones tras pulsar).

> Importante: ningún archivo nuevo de `app/` debe existir antes de su primer test rojo. La factoría de modelos y los routers solo se cablean cuando un test los exige.

---

## 5. Smoke tests manuales (post-implementación)

Asumiendo dos usuarios registrados `alice` y `bob`, y un tercero `carl` para los casos de búsqueda con varios resultados:

### 5.1 Buscar usuarios

1. Login como `alice`.
2. En el header, escribir `bob` en el `UserSearchBar`.
3. **Esperado**: dropdown con `bob` y otros nicknames que contengan `bob`. `alice` NO aparece aunque su nickname contuviera `bob` parcialmente.
4. Buscar texto que no coincida con ninguno (`zzz`). **Esperado**: estado vacío informativo, sin error.
5. Buscar con campo vacío. **Esperado**: dropdown cerrado o mensaje "Escribe para buscar"; sin llamada al backend.
6. Buscar `BOB`. **Esperado**: mismos resultados que `bob` (case-insensitive).

### 5.2 Visualizar perfil ajeno

1. Desde el dropdown, clic sobre `bob`.
2. Navega a `/users/bob`.
3. **Esperado**: avatar de bob, nickname, juegos vinculados (LoL si aplica), datos públicos del juego en tiempo real (igual que en `/profile` propio). NO hay opciones de edición ni botón "Eliminar cuenta". Sí hay un único botón de relación.
4. URL directa a un nickname inexistente (`/users/no-existe`). **Esperado**: 404 con mensaje "Usuario no encontrado".
5. URL directa a un nickname anonimizado (`deleted-XXXXXXXX`). **Esperado**: 404.

### 5.3 Enviar solicitud y comprobar estado "Pendiente"

1. En `/users/bob`, botón "Añadir amigo".
2. Pulsar. **Esperado**: 201, botón pasa a "Pendiente" y queda deshabilitado.
3. Recargar la página. **Esperado**: el botón sigue como "Pendiente" (lo dicta el backend a través de `relationship_status`).
4. En la BD: `SELECT * FROM friendships WHERE requester_id = alice.id AND addressee_id = bob.id` → una fila con `status='pending'`.
5. Intentar volver a enviar (vía `POST` directo): **Esperado**: 409.

### 5.4 Aceptar una solicitud (con la API directa, sin UI)

> La UI del panel principal está fuera de alcance esta fase. La aceptación se prueba con `curl` o herramientas equivalentes.

1. Login como `bob`.
2. `GET /api/friends/requests` → lista con la solicitud de `alice` (incluye `id` de la solicitud).
3. `POST /api/friends/request/{request_id}/accept`. **Esperado**: 200 con `relationship_status: AMIGO`.
4. En `alice`: recargar `/users/bob` (o re-buscar). **Esperado**: el botón ahora es "Eliminar amigo".
5. En BD: la fila pasó a `status='accepted'`. No se ha creado una fila simétrica.

### 5.5 Rechazar una solicitud

1. Como en 5.3 pero con un nuevo par. `bob` recibe solicitud de `carl`.
2. Como `bob`: `POST /api/friends/request/{request_id}/reject`. **Esperado**: 200 con `relationship_status: SIN_RELACION`.
3. En BD: la fila se ha borrado.
4. Como `carl`: en `/users/bob`, el botón vuelve a "Añadir amigo". Puede volver a pulsar y enviar otra solicitud (no hay bloqueo persistente).

### 5.6 Eliminar amigo (bidireccional)

1. `alice` y `bob` son amigos.
2. Como `alice`, en `/users/bob`, pulsar "Eliminar amigo".
3. **Esperado**: 204, botón vuelve a "Añadir amigo".
4. Como `bob`, ir a `/users/alice` (o buscar). **Esperado**: el botón también es "Añadir amigo" (la amistad se eliminó simétricamente sin segunda acción).
5. En BD: ninguna fila con `status='accepted'` entre los dos.

### 5.7 Auto-solicitud bloqueada

1. Como `alice`: `POST /api/friends/request/{alice.id}`. **Esperado**: 400 "No puedes enviarte una solicitud a ti mismo."

### 5.8 Solicitud cruzada (race coherente)

1. `alice` envía solicitud a `bob`. **Esperado**: 201.
2. Inmediatamente, `bob` intenta enviar solicitud a `alice` (vía API). **Esperado**: 409 con mensaje "Este usuario ya te ha enviado una solicitud; acéptala desde tu panel."
3. `bob` puede aceptar la solicitud existente vía `accept`.

---

## 6. Resolución de problemas habituales

| Síntoma | Causa probable | Acción |
|---------|----------------|--------|
| `GET /api/friends/search` devuelve siempre `[]` aun con resultados esperados | Estás autenticado como el único usuario que coincide con `q`; te excluyes a ti mismo | Probar con un segundo usuario o ajustar la query |
| `POST /api/friends/request/{user_id}` devuelve 409 inesperadamente | Existe una fila previa (pending o accepted) en cualquier dirección | `SELECT * FROM friendships WHERE (requester_id IN (a,b) AND addressee_id IN (a,b))` para diagnosticar |
| Tras aceptar una solicitud, el botón en `alice` sigue como "Pendiente" hasta refresh | Componente no refetch al volver a foco | Asegúrate de que `UserProfile.jsx` re-fetcha al volver a foco; el backend ya devuelve el estado correcto |
| `pytest` falla con "table friendships does not exist" | Migración no aplicada | `alembic upgrade head` |
| Tests de Vitest fallan con "Network request failed" | MSW no está registrando los handlers de friends | Comprobar `tests/mocks/server.js` incluye `friendsHandlers` |
| `GET /api/profile/{nickname}` devuelve 200 con `email` poblado | Estás devolviendo el esquema del propio perfil en lugar del público | El esquema `PublicProfileResponse` NO incluye `email` |

---

## 7. Comandos útiles

```bash
# Generar nueva migración tras tocar models/
alembic revision --autogenerate -m "add friendships"
alembic upgrade head

# Lint backend
ruff check backend/

# Cobertura de tests backend
pytest --cov=app --cov-report=term-missing

# Cobertura de tests frontend
cd frontend && npm run test:coverage
```

---

## 8. Definition of Done para 004-add-friends

- [ ] `pytest` pasa al 100% (unit + integration) localmente y en CI.
- [ ] `npm run test:run` pasa al 100% en frontend.
- [ ] Cobertura backend ≥ la base de 003 (no regresión).
- [ ] Smoke tests 5.1 a 5.8 ejecutados manualmente con éxito.
- [ ] Migración Alembic creada, aplicada y reversible (`upgrade` + `downgrade`).
- [ ] `requirements.txt` y `package.json` sin altas (la feature no introduce dependencias).
- [ ] No queda ninguna referencia a `prompts/` en código productivo (Constitución V).
- [ ] No quedan marcadores `NEEDS CLARIFICATION` en plan/research.
- [ ] PR con checklist de constitución marcada.
