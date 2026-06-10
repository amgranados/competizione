# Quickstart — 003-edit-profile

**Branch**: `003-edit-profile` | **Date**: 2026-04-25
**Stack input (humano)**: `prompts/second/03-perfil.txt` (Constitución V — input histórico).

Este documento sirve como guía operativa para arrancar la feature en local, ejecutar el flujo TDD y comprobar manualmente los cuatro flujos clave del perfil.

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
RIOT_API_KEY=RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

> Si **no** se define `RIOT_API_KEY`, `get_riot_api_client(settings)` devuelve `MockRiotAPIClient` con log `INFO Using MockRiotAPIClient: RIOT_API_KEY not set`. El sistema sigue siendo navegable pero los datos LoL serán los sembrados por el mock.

`frontend/.env` (sin variables nuevas en esta iteración).

---

## 2. Instalación

```bash
# Backend
cd backend
python -m venv .venv
. .venv/Scripts/activate          # Windows / bash
pip install -r requirements.txt   # ya incluye respx tras 003

# Migraciones
alembic upgrade head              # aplica add_avatar_and_riot_account

# Frontend
cd ../frontend
npm install
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
- **`/profile`** — nueva en 003.

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
pytest tests/unit/test_profile_service.py::test_update_nickname_rejects_duplicate -q
```

```bash
# Frontend
cd frontend
npm run test                       # interactivo
npm run test:run                   # one-shot CI-mode
npm run test:coverage
```

### Orden sugerido de Red → Green → Refactor

1. `tests/unit/test_profile_service.py::test_update_nickname_*`
   - `test_update_nickname_accepts_unique`
   - `test_update_nickname_rejects_duplicate`
   - `test_update_nickname_idempotent_when_same_as_current`
2. `tests/unit/test_profile_service.py::test_change_password_*`
3. `tests/unit/test_profile_service.py::test_update_avatar_url_*` (validación HttpUrl, null permitido)
4. `tests/unit/test_riot_api_client.py::test_mock_*` (nuevos métodos del Mock)
5. `tests/unit/test_riot_api_client.py::test_http_*` (con `respx`)
6. `tests/unit/test_profile_service.py::test_link_lol_*` (con `MockRiotAPIClient` inyectado)
7. `tests/unit/test_profile_service.py::test_unlink_lol_*` (incluye bloqueo por torneo activo)
8. `tests/unit/test_profile_service.py::test_delete_account_*` (confirmación, bloqueo, anonimización, blacklist)
9. `tests/integration/test_profile_routes.py` — cablea endpoints; cada test exige una ruta concreta y se hace pasar implementándola.
10. Frontend: `tests/unit/ProfileForm.test.jsx` → `tests/integration/Profile.test.jsx` → `tests/integration/DeleteAccountModal.test.jsx`.

> Importante: ningún archivo nuevo de `app/` debe existir antes de su primer test rojo. La factoría `get_riot_api_client` ya existe (002); en 003 solo se elimina el `NotImplementedError` cuando hay tests del `HttpRiotAPIClient` que lo exigen.

---

## 5. Smoke tests manuales (post-implementación)

Asumiendo dos usuarios registrados `alice` (con cuenta de Riot real) y `bob` (sin Riot vinculado), y al menos un torneo activo en el que `alice` participa:

### 5.1 Visualizar perfil

1. Login como `alice`.
2. Ir a `/profile`.
3. **Esperado**: avatar, nickname, sección "Juegos vinculados" con LoL si está vinculado, datos en tiempo real de Riot. Si la API devuelve fallo en una sección, esa sección muestra "no disponible temporalmente" sin tirar el resto.

### 5.2 Cambiar nickname

1. En `/profile`, modificar el nickname a uno libre (ej. `aliceX`).
2. **Esperado**: 200, nickname actualizado, header/avatar reflejan el nuevo valor.
3. Repetir intentando poner el nickname de `bob`. **Esperado**: 409, mensaje "Nickname no disponible".
4. Repetir poniendo el nickname **actual** de `alice`. **Esperado**: 200 sin error.

### 5.3 Cambiar contraseña

1. Login como `alice`. En otra pestaña/incognito, **iniciar sesión también como `alice`** (segunda sesión).
2. En la sesión 1, cambiar contraseña con la nueva contraseña válida (≥8 chars).
3. **Esperado en sesión 1**: 204, sigue navegable (sus cookies se han rotado).
4. **Esperado en sesión 2**: cualquier petición autenticada → 401 (refresh ya en blacklist).
5. Logout y login en cualquier sesión: solo funciona la **nueva** contraseña.

### 5.4 Cambiar avatar

1. Pegar una URL HTTP válida (ej. `https://i.imgur.com/xxxx.png`) en el campo de avatar.
2. **Esperado**: 200, avatar actualizado en `/profile`. (El frontend usa `object-fit: cover` para presentación uniforme aunque la imagen no sea cuadrada.)
3. Probar URL inválida (`not a url`). **Esperado**: 400.
4. Borrar el avatar (enviar `null`). **Esperado**: 200, vuelve al avatar por defecto.

### 5.5 Vincular LoL

1. Como `bob` (sin Riot vinculado).
2. Sección "Juegos vinculados" → botón "Vincular LoL".
3. Introducir `game_name`, `tag_line` y `region` válidos.
4. **Esperado**: 201, sección muestra los datos públicos.
5. Repetir con tag_line erróneo. **Esperado**: 400, mensaje genérico "No se pudo vincular la cuenta de Riot. Verifica los datos introducidos."
6. Inspeccionar BD: `SELECT * FROM riot_accounts WHERE user_id = bob.id` → solo `puuid` + `region` + `linked_at`. **Nunca** se ven `game_name`/`tag_line`.
7. Inspeccionar logs del request: ni `game_name` ni `tag_line` aparecen.

### 5.6 Desvincular LoL

1. Como `alice`, que participa en un torneo activo de LoL.
2. Botón "Desvincular".
3. **Esperado**: 409, "No puedes desvincular mientras participes en un torneo activo del juego".
4. Como `bob`, sin torneos activos.
5. **Esperado**: 204, sección vuelve a "no vinculado".

### 5.7 Eliminar cuenta

1. Como `bob` (sin torneos activos).
2. "Eliminar cuenta" → modal con input.
3. Escribir un texto distinto del nickname → botón deshabilitado.
4. Escribir el nickname exacto → botón habilitado → confirmar.
5. **Esperado**: 204, redirección a `/login`. Intentar login con las credenciales antiguas → 401 (password_hash sentinel).
6. Como `alice`, que participa en un torneo activo. Repetir el flujo. **Esperado**: 409, mensaje "Tienes torneos activos...".
7. Verificar en BD: `SELECT email, nickname, deleted_at FROM users WHERE id = bob.id` → `email = NULL`, `nickname = deleted-XXXXXXXX`, `deleted_at` con timestamp.
8. Verificar integridad histórica: torneos cerrados en los que `bob` participaba siguen mostrando "deleted-XXXXXXXX" en lugar de su nickname original; las posiciones/clasificaciones se conservan.

---

## 6. Resolución de problemas habituales

| Síntoma | Causa probable | Acción |
|---------|----------------|--------|
| `GET /api/profile` siempre devuelve `unavailable: true` en todas las secciones | `RIOT_API_KEY` ausente y los smoke tests asumen real → mock no tiene datos sembrados para ese PUUID | Sembrar el mock en el test fixture o exportar `RIOT_API_KEY` |
| `PATCH /api/profile/avatar` rechaza una URL válida | El esquema valida `HttpUrl` → URL sin `http(s)://` | Añadir el esquema |
| `POST /api/profile/link/lol` siempre devuelve 503 en CI | Tests de integración que llaman a Riot real (no es lo que queremos) | Usar `MockRiotAPIClient` vía dependency override |
| Tests de `respx` se cuelgan | Cliente real escapa al mock por host distinto | Verificar que `HttpRiotAPIClient` use el host configurado y que `respx.mock` haga match con ese host |
| `pytest` falla con "table riot_accounts does not exist" | Migración no aplicada | `alembic upgrade head` |

---

## 7. Comandos útiles

```bash
# Generar nueva migración tras tocar models/
alembic revision --autogenerate -m "add avatar_url and riot_accounts"
alembic upgrade head

# Lint backend
ruff check backend/

# Lint frontend
# (no configurado en esta iteración; los tests cubren regresiones funcionales)

# Cobertura de tests backend
pytest --cov=app --cov-report=term-missing

# Cobertura de tests frontend
cd frontend && npm run test:coverage
```

---

## 8. Definition of Done para 003-edit-profile

- [ ] `pytest` pasa al 100% (unit + integration) localmente y en CI.
- [ ] `npm run test:run` pasa al 100% en frontend.
- [ ] Cobertura backend ≥ la base de 002 (no regresión).
- [ ] Smoke tests 5.1 a 5.7 ejecutados manualmente con éxito.
- [ ] Migración Alembic creada, aplicada y reversible (`upgrade` + `downgrade`).
- [ ] `requirements.txt` incluye `respx` y el lockfile/registro CVE refleja la nueva dep.
- [ ] No queda ninguna referencia a `prompts/` en código productivo (Constitución V).
- [ ] No quedan marcadores `NEEDS CLARIFICATION` en plan/research.
- [ ] PR con checklist de constitución marcada.
