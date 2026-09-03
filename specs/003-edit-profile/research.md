# Phase 0 — Research: Editar perfil de usuario

**Branch**: `003-edit-profile` | **Date**: 2026-04-25
**Input**: [plan.md](./plan.md), [spec.md](./spec.md), `prompts/second/03-perfil.txt` (input histórico, Constitución V)

Este documento consolida las decisiones técnicas tomadas para resolver el plan, agrupadas por bloque. El stack está fijado por el humano (Constitución IV), por lo que esta sección **no evalúa alternativas de stack**: solo decisiones de cómo aplicar lo fijado.

---

## Scope

### Decisión

El alcance backend de FR-017 / FR-018 / FR-019 / FR-020 (subir foto, límite de peso, recorte cuadrado, foto por defecto) se reduce a **almacenar y devolver una URL validada** mediante `HttpUrl` de Pydantic v2. No hay subida ni recorte ni inspección del contenido en backend.

### Rationale

El prompt fija textualmente: "Foto de perfil: se almacena como URL en la base de datos. El backend valida únicamente que el valor sea una URL bien formada (HttpUrl de Pydantic). No se realiza ninguna petición externa para verificar el contenido." (Constitución IV: el humano fija el cómo). La spec describe la **intención** (peso, cuadrado), pero el cómo backend está intencionadamente fuera de alcance esta iteración.

### Alternativas consideradas (rechazadas)

- **Upload+crop server-side con Pillow**: rechazado. Añade dependencia (Pillow), almacenamiento, política de límites, y violaría Constitución IV.
- **Upload directo a S3/R2 con presigned URL**: rechazado. No pedido por el prompt; introduciría infraestructura nueva.
- **Validar disponibilidad HEAD-request a la URL**: rechazado por el prompt ("No se realiza ninguna petición externa para verificar el contenido").

### Trazabilidad spec → backend

- FR-017 → backend acepta URL en formatos típicos siempre que el host la sirva como imagen; el backend NO discrimina por formato.
- FR-018 (peso máximo) → fuera del backend.
- FR-019 (recorte cuadrado) → fuera del backend; el frontend renderiza con `object-fit: cover` para que la representación sea uniforme aun si la imagen no es cuadrada (decisión de presentación, no contractual).
- FR-020 (foto por defecto) → si `users.avatar_url` es `null`, el frontend muestra un avatar por defecto (recurso estático del bundle).

---

## HD-1: Validador de contraseña reutilizado de 001

### Decisión

La validación de la nueva contraseña en `PATCH /api/profile/password` reutiliza la misma función/criterios usados en el registro/login de 001-user-auth (mínimo 8 caracteres, según el prompt y consolidado en 001).

### Rationale

Constitución IV (no reinventar). El validador ya existe y es testeable.

### Alternativas

- Política reforzada (mayúsculas, dígitos, símbolos): rechazada. El prompt fija ≥8 caracteres y nada más.
- Política dual (registro vs cambio): rechazada. Aumenta superficie cognitiva sin justificación.

---

## HD-2: Cadena de confirmación para eliminación de cuenta

### Decisión

El usuario debe escribir **su nickname actual exacto** (case-sensitive, sin espacios alrededor) en el modal de confirmación. Si no coincide, el botón "Eliminar cuenta" permanece deshabilitado en el frontend y el backend rechaza la operación con `400 Bad Request`.

### Rationale

- Personaliza la cadena (no copia-pega genérico "ELIMINAR").
- Se traduce solo (es el dato del propio usuario).
- Forzar a teclear el nombre obliga a un acto consciente y reduce el riesgo de borrado accidental.
- Coherente con prácticas de GitHub/GitLab al borrar repos.

### Alternativas

- "ELIMINAR" o "BORRAR" (texto fijo): rechazado por menos personalización.
- Email del usuario: rechazado; el email puede no estar a la vista del propio usuario en el modal y aumenta fricción.
- Doble confirmación con click temporizado: rechazado por mayor complejidad UI sin pruebas de mejor protección.

### Verificación testable

- `test_profile_service.py::test_delete_account_rejects_wrong_confirmation`
- `test_profile_routes.py::test_delete_account_400_when_confirmation_mismatch`
- `DeleteAccountModal.test.jsx` integra: escribir el nickname habilita el botón.

---

## HD-3: Concurrencia de llamadas Riot al cargar el perfil

### Decisión

Las 4 llamadas a Riot (`get_summoner_profile`, `get_ranked_stats`, `get_champion_mastery`, `get_recent_matches`) se disparan **en paralelo** con `asyncio.gather(..., return_exceptions=True)`. Cada sección de la respuesta se rellena de forma independiente: si una falla, su sub-objeto del response se devuelve como `null` con un campo `unavailable: true`; el resto del perfil llega completo.

### Rationale

- SC-007 fija <5 s; en serie, 4 latencias medias se acumularían.
- `return_exceptions=True` evita que un solo fallo (por ejemplo, maestría sin datos) tire toda la respuesta.
- El prompt no obliga a transaccionalidad entre las 4 fuentes; son secciones independientes.

### Alternativas

- Llamadas en serie: rechazada por SC-007.
- "Fail-fast" (cualquier fallo → 503 global): rechazado por degradar UX más de lo necesario; el spec FR-016 explícitamente pide "no disponible temporalmente" sin afectar al resto.

### Verificación testable

- `test_riot_api_client.py::test_http_client_timeout_per_endpoint` (timeout independiente por método).
- `test_profile_routes.py::test_get_profile_partial_riot_failure` con `respx`: `get_recent_matches` 503 → resto OK, `recent_matches` viene como `null`.

---

## HD-4: Estrategia de eliminación de cuenta — anonimización vs hard-delete

### Decisión

**Anonimización**, no eliminación física. La fila de `users` permanece con:

- `email = NULL`
- `nickname = "deleted-{first 8 chars of new uuid7}"` (sigue cumpliendo unicidad)
- `password_hash = "!"` (string sentinel imposible de validar)
- `failed_login_attempts = 0`, `locked_until = NULL`
- **Nuevo**: `deleted_at = now()`
- `avatar_url = NULL`

Las filas en tablas hijas (`participants`, `tournaments` como organizador, `matches`, `notifications`, `riot_accounts`) **no se tocan**; el FK sigue apuntando a la fila anonimizada. La fila de `riot_accounts` asociada al usuario eliminado se borra (`DELETE`, no anonimización: el PUUID/region son datos personales del juego del usuario y no aportan integridad histórica relevante).

Las sesiones del usuario se invalidan (todas las refresh tokens se añaden a la blacklist) y la sesión actual se cierra (cookie clear).

### Rationale

- **Integridad histórica de torneos** (002): si se hace hard-delete, los `participants.user_id` quedarían huérfanos (FK on delete → SET NULL o CASCADE rompería ranking/historia). La anonimización mantiene el grafo intacto.
- **Cumplimiento "datos personales eliminados"** del FR-024: los campos identificables (email, nickname original, foto) se neutralizan.
- Permite mostrar en clasificaciones cerradas un nombre genérico ("deleted-xxxx") sin exponer al usuario eliminado.

### Alternativas

- Hard-delete con `ON DELETE CASCADE`: rechazado por pérdida de integridad histórica.
- `ON DELETE SET NULL` y luego mostrar "(usuario eliminado)" cada vez: rechazado; obliga a manejar `NULL` en todos los joins de torneo (más cambios cross-feature).
- Tabla `archived_users` separada: rechazado; añade una tabla y migración sin necesidad demostrada.

### Verificación testable

- `test_profile_service.py::test_delete_account_anonymizes_user_row`
- `test_profile_service.py::test_delete_account_keeps_tournament_history_intact`
- `test_profile_service.py::test_delete_account_invalidates_all_refresh_tokens`

---

## HD-5: Cambio de contraseña e invalidación de sesiones

### Decisión

Al cambiar la contraseña con éxito:

1. Se rota el access token y refresh token de la sesión actual (el frontend recibe nuevas cookies en la respuesta).
2. **Todos los demás refresh tokens activos del usuario se añaden a la blacklist** mediante el mecanismo ya existente en 001 (`token_blacklist`).
3. La sesión actual queda válida y operativa.

### Rationale

- FR-009 lo exige sin definir el "cómo".
- El mecanismo de blacklist existe desde 001; reutilizarlo cumple Constitución IV.
- Mantener viva la sesión actual evita auto-logout abrupto (mejor UX).

### Alternativas

- Cerrar **todas** las sesiones, incluida la actual: rechazado; obliga a re-login redundante tras una operación que el usuario acaba de autenticar.
- No invalidar nada: rechazado; viola FR-009.

### Verificación testable

- `test_profile_service.py::test_change_password_blacklists_other_sessions`
- `test_profile_routes.py::test_change_password_keeps_current_session_valid`

---

## HD-6: Política de descarte de credenciales del videojuego

### Decisión

Las credenciales de Riot (`game_name` y `tag_line`) recibidas en `POST /api/profile/link/lol`:

1. Llegan en el body JSON (no por URL).
2. Se usan **únicamente** dentro del scope del request handler para resolver el PUUID vía Riot API.
3. **Nunca** se loguean (logs configurados para no incluir el body de este endpoint, y el código `profile_service.link_lol()` no construye logs con esos campos).
4. **Nunca** se persisten en BD ni en cookies ni en headers de respuesta.
5. Tras resolver el PUUID, las variables locales que contienen `game_name`/`tag_line` salen del scope y son liberables por el GC.
6. El log de éxito de la operación incluye solo `user_id` y `puuid` resultante.

### Rationale

- FR-012 y SC-003 lo exigen.
- HD-6 hace explícito el patrón para que sea testeable en revisión de código.

### Verificación testable

- `test_profile_service.py::test_link_lol_does_not_persist_credentials` (al inspeccionar `riot_accounts` no aparecen `game_name`/`tag_line`).
- Test estático de **revisión de logs**: pytest captura stdout/log del handler con `caplog` y comprueba que ni `game_name` ni `tag_line` aparecen en ningún registro.

---

## HD-7: Mensajes de error en vinculación Riot

### Decisión

El backend devuelve dos tipos de error en `POST /api/profile/link/lol`:

| Causa | Status | Body |
|-------|--------|------|
| Riot ID inexistente, `game_name`/`tag_line` mal escritos, cuenta bloqueada por Riot, cualquier 4xx de Riot relacionado con identidad | `400 Bad Request` | `{"detail": "No se pudo vincular la cuenta de Riot. Verifica los datos introducidos."}` |
| Riot devuelve 5xx, timeout, connection error | `503 Service Unavailable` | `{"detail": "Riot no está disponible temporalmente. Inténtalo de nuevo en unos minutos."}` |

Para FR-016 (carga del perfil con Riot caído), las secciones de LoL afectadas devuelven `null + unavailable: true` con HTTP 200 global (perfil cargado, partes degradadas).

### Rationale

- FR-013 y SC-008 fuerzan que NO se distinga entre identificador inválido y "contraseña incorrecta del videojuego". (Nota: el flujo Riot ID/PUUID **no usa contraseña del videojuego**; la spec habla de "credenciales del videojuego" en sentido amplio. La política se cumple porque cualquier fallo de identidad/autenticación con Riot da el mismo mensaje.)
- Distinguir `400` (entrada del usuario) vs `503` (disponibilidad) es estándar HTTP y no viola SC-008 (las dos categorías son ortogonales).

### Verificación testable

- `test_profile_routes.py::test_link_lol_400_for_unknown_riot_id`
- `test_profile_routes.py::test_link_lol_400_for_4xx_from_riot` (con `respx` simulando 401/403/404)
- `test_profile_routes.py::test_link_lol_503_for_riot_5xx` (con `respx` simulando 500/503/timeout)

---

## TDD Workflow

Aplicación literal del Principio II (NO NEGOCIABLE).

### Orden de los ciclos Red → Green → Refactor

1. **Esquemas Pydantic v2** (`schemas/profile.py`): tests de validación (test fallido → implementar mínimo).
2. **Modelo `RiotAccount`** (`models/riot_account.py`): test de creación + unicidad de PUUID por usuario; migración Alembic implementada para hacer pasar el test de integración correspondiente.
3. **Extensión del Protocol `RiotAPIClient`** (`services/riot_api/client.py`): tests del Mock primero (datos sembrados → respuesta esperada). Solo cuando todos los métodos del Mock estén verdes, se aborda el `HttpRiotAPIClient`.
4. **`HttpRiotAPIClient`** (`services/riot_api/http_client.py`): tests con `respx` por método y escenario (200/4xx/5xx/timeout). Cada test rojo desbloquea una porción del cliente.
5. **`profile_service`** (`services/profile_service.py`): tests unitarios por flujo (nickname, password, avatar, link, unlink, delete) usando `MockRiotAPIClient` inyectado.
6. **Rutas FastAPI** (`api/routes/profile.py`): tests de integración con `httpx.AsyncClient`. Solo se cablean al main cuando los tests de `profile_service` estén verdes.
7. **Frontend**:
   - Unit (`ProfileForm.test.jsx`): el componente expone los handlers correctos; con MSW el cambio de nickname dispara `PATCH /api/profile/nickname`.
   - Integración (`Profile.test.jsx`, `DeleteAccountModal.test.jsx`): flujos completos con MSW.

### Estructura de fixtures (`conftest.py`)

Fixtures nuevos:

- `user_with_avatar` y `user_without_avatar`.
- `user_with_riot_account` (PUUID, region).
- `mock_riot_client` (instancia de `MockRiotAPIClient` con datos sembrados realistas).
- Override de la dependencia `get_riot_api_client` en tests para inyectar el mock.

---

## Dependencies & CVE Audit

### Dependencias añadidas

| Paquete | Versión | Tipo | Motivo |
|---------|---------|------|--------|
| `respx` | `>=0.21` | test-only | Mock de `httpx` para `test_riot_api_client.py` (Constitución II). Pinned como mínimo; la última stable es la deseable. |

### Dependencias re-utilizadas (sin cambios)

`fastapi`, `sqlalchemy[asyncio]`, `alembic`, `asyncpg`, `aiosqlite`, `pydantic[email]`, `pydantic-settings`, `PyJWT`, `passlib[bcrypt]`, `bcrypt`, `python-multipart`, `slowapi`, `httpx`, `pytest`, `pytest-asyncio`, `pytest-cov`. Frontend sin altas.

### CVE audit

- **respx**: paquete maduro (>4 años, mantenido por `lundberg`). Búsqueda en NIST NVD el 2026-04-25: **sin CVEs conocidas**. Es una librería de tests, sin presencia en runtime productivo. ✅ apto.
- **httpx**: ya en uso en el proyecto desde 001/002. Sin nuevos CVEs relevantes a la versión ≥0.27 fijada. ✅
- **Pydantic v2**: ya en uso. `HttpUrl` no abre nuevas superficies. ✅

> Constitución I obliga a auditar antes de instalar. La instalación efectiva ocurre cuando `/speckit.tasks` genere la tarea correspondiente y `/speckit.implement` la ejecute; este audit queda registrado aquí para trazabilidad.

---

## Riot API — endpoints concretos consumidos

Los métodos del Protocol mapean a estos endpoints (todos GET, header `X-Riot-Token: $RIOT_API_KEY`):

| Método del Protocol | Endpoint Riot | Notas |
|---------------------|---------------|-------|
| (interno, dentro de `link_lol`) | `/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}` | Resuelve `puuid`. Usa la región **regional** (`europe.api.riotgames.com` o equivalente). |
| `get_summoner_profile(puuid)` | `/lol/summoner/v4/summoners/by-puuid/{puuid}` | Devuelve `summonerLevel` + `id` interno; el "servidor" se reporta como la región configurada del PUUID (almacenada en `riot_accounts.region`). |
| `get_ranked_stats(puuid)` | `/lol/league/v4/entries/by-puuid/{puuid}` | Lista de queues (RANKED_SOLO_5x5, RANKED_FLEX_SR). Se filtran las dos relevantes. |
| `get_champion_mastery(puuid, limit=5)` | `/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/top?count=5` | Top 5 maestrías. |
| `get_recent_matches(puuid, limit=5)` | `/lol/match/v5/matches/by-puuid/{puuid}/ids?count=5` + `/lol/match/v5/matches/{matchId}` por cada uno | Pareja de llamadas; se paralelizan internamente. Devuelve resumen mínimo necesario para el frontend. |

La región para los endpoints de "match" vs "league/summoner" sigue el split de Riot (regional vs platform). El cliente HTTP encapsula esto y la `region` que el usuario indica en la vinculación se almacena con el formato platform (p. ej. `EUW1`); el cliente la mapea a regional (`europe`) cuando hace falta.

### Decisión sobre validación de la región durante la vinculación

La región se acepta del input del usuario en la vinculación. Set permitido (whitelist): `EUW1`, `EUN1`, `NA1`, `KR`, `BR1`, `LA1`, `LA2`, `OC1`, `JP1`, `RU`, `TR1`. Cualquier otro valor → `400 Bad Request` con el mensaje genérico de HD-7.

---

## Riesgos identificados

| Riesgo | Mitigación |
|--------|------------|
| Latencia acumulada de 4 llamadas Riot por carga de perfil | Llamadas en paralelo (HD-3) + timeout 2 s por método |
| Rate limit de Riot (dev key 100/2 min) | Sin caché en esta iteración (impuesto por prompt). Si en producción se observa rate limit, se evaluará caché en feature posterior. |
| Cambios contractuales de Riot | Encapsulados en `HttpRiotAPIClient`; el resto del sistema solo conoce el Protocol y los DTOs. |
| Riot ID + tag_line escritos con espacios | Se hace `strip()` antes de enviar a Riot. Los espacios internos sí se preservan (Riot los acepta). |
| Pérdida de integridad histórica al borrar cuenta | Anonimización (HD-4) en lugar de hard-delete |
| Reactivación accidental del FR-004 de 002 (bloqueo desvinculación) sin tests | El test `test_unlink_lol_blocked_by_active_tournament` se exige antes del implement (TDD). |

---

## Resultado

Phase 0 cierra **sin marcadores `NEEDS CLARIFICATION`**. Todas las preguntas que no resolvía la spec (cadena de confirmación, estrategia de borrado, paralelismo Riot, política de logs, mensaje de error genérico) se han fijado como decisiones humanas (HD-2 a HD-7), trazables y testeables.
