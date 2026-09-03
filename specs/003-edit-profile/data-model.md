# Phase 1 — Data Model: Editar perfil de usuario

**Branch**: `003-edit-profile` | **Date**: 2026-04-25
**Source**: derivado de [spec.md](./spec.md), constraints en [plan.md](./plan.md), decisiones en [research.md](./research.md).

Esta iteración **extiende** dos entidades existentes y **añade** una. Las entidades de 001 (`User`, `TokenBlacklist`) y 002 (`Tournament`, `Participant`, `Invitation`, `Match`, `Notification`) se mencionan solo en la medida en que sus invariantes participan en este modelo (bloqueos cruzados).

---

## Resumen

| Entidad | Tipo | Cambio en esta iteración |
|---------|------|--------------------------|
| `User` | extendida | Añade `avatar_url` (nullable) y `deleted_at` (nullable) |
| `RiotAccount` | **nueva** | 1:1 con `User`; persiste PUUID y región. **Nunca contiene credenciales.** |
| `Tournament`, `Participant` | sin cambios estructurales | Se consultan en lectura para bloquear desvinculación / eliminación |
| `TokenBlacklist` | sin cambios estructurales | Se inserta en bloque al cambiar contraseña / eliminar cuenta |

---

## 1. `User` (extendida)

Tabla existente desde 001. Atributos añadidos en esta iteración:

| Campo | Tipo | Nullable | Default | Notas |
|-------|------|----------|---------|-------|
| `avatar_url` | `String(2048)` | sí | `NULL` | URL HTTP/HTTPS validada a nivel de aplicación (Pydantic `HttpUrl`). En BD se almacena como string. Si es `NULL`, el frontend muestra avatar por defecto. |
| `deleted_at` | `DateTime(timezone=True)` | sí | `NULL` | Marca de anonimización. Si está presente, la cuenta está eliminada (HD-4). |

### Reglas de validación (a nivel servicio + esquema)

- `avatar_url`:
  - Debe parsear como `HttpUrl` (Pydantic v2). Esquemas: `http`, `https`.
  - Longitud máxima 2048 chars (límite de columna).
  - El backend NO realiza ninguna petición externa para verificar el contenido (HD: Scope).
- `nickname` (campo existente, regla nueva derivada de FR-006):
  - Validación de unicidad case-sensitive contra `users.nickname` excluyendo el propio usuario; si el nuevo nickname coincide exactamente con el actual, se acepta como no-op (200 OK).
  - Reglas de longitud y caracteres permitidos: las que ya impone 001 (no se redefinen aquí).
- `password_hash` (campo existente):
  - El cambio se realiza con la misma función de hash (`passlib[bcrypt]`) usada en 001.
  - La nueva contraseña en claro se valida con la misma política de 001 (≥8 chars).

### Anonimización (eliminación de cuenta — HD-4)

Cuando un `User` se elimina vía `DELETE /api/profile/me`:

| Campo | Antes | Después |
|-------|-------|---------|
| `email` | `user@example.com` | `NULL` |
| `nickname` | `OldNick` | `deleted-{8-char-uuid7-suffix}` |
| `password_hash` | hash bcrypt | `"!"` (sentinel inválido) |
| `failed_login_attempts` | n | `0` |
| `locked_until` | datetime o NULL | `NULL` |
| `avatar_url` | URL o NULL | `NULL` |
| `deleted_at` | `NULL` | `now()` |
| `id` | UUID | **inmutable** (preserva FK desde participants/tournaments) |
| `created_at` | datetime | **inmutable** |

**Invariante post-condición**: tras anonimizar, no debe ser posible:
- Iniciar sesión como ese usuario (`password_hash = "!"` lo impide).
- Vincular la cuenta a Riot (la fila no aparece como destino en `/api/profile/link/lol` porque su sesión está cerrada y los tokens revocados).
- Recuperar el email original ni el nickname original.

---

## 2. `RiotAccount` (nueva)

Tabla nueva. Representa la cuenta de League of Legends vinculada a un usuario.

```text
Table: riot_accounts
```

| Campo | Tipo | Nullable | Default | Constraints |
|-------|------|----------|---------|-------------|
| `id` | `Uuid` | no | `uuid4()` | PK |
| `user_id` | `Uuid` | no | — | FK → `users.id` ON DELETE CASCADE; **UNIQUE** (un usuario solo puede tener una cuenta de LoL vinculada en esta iteración) |
| `puuid` | `String(78)` | no | — | UNIQUE; identificador estable del jugador en Riot |
| `region` | `String(8)` | no | — | Whitelist: `EUW1`, `EUN1`, `NA1`, `KR`, `BR1`, `LA1`, `LA2`, `OC1`, `JP1`, `RU`, `TR1` |
| `linked_at` | `DateTime(timezone=True)` | no | `now()` | Trazabilidad |

### Reglas

- **Nunca** se almacena `game_name` ni `tag_line` (Riot ID en claro). Solo el `puuid` derivado de la llamada a `/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}`.
- Crear una `RiotAccount` para un `user_id` que ya tiene una existente → `409 Conflict` o se trata como "actualización" según el contrato (ver `contracts/profile.openapi.yaml`). Decisión actual: **rechazar con `409`** y exigir desvinculación previa para mayor claridad.
- Si el usuario tiene `deleted_at` no nulo, no debe existir `RiotAccount` (se borra durante la anonimización).
- ON DELETE CASCADE garantiza que si por cualquier vía se hace hard-delete del usuario (no es el caso normal), la fila de Riot también se elimina.

### Bloqueo de desvinculación

`DELETE /api/profile/link/lol` se rechaza con `409 Conflict` si:

```text
EXISTS (
  SELECT 1
  FROM participants p
  JOIN tournaments t ON p.tournament_id = t.id
  WHERE p.user_id = :user_id
    AND p.removed = false
    AND t.state IN ('open', 'in_progress')
)
```

(El estado `'open'` corresponde a "Inscripción abierta" y `'in_progress'` a "En curso", siguiendo la nomenclatura del modelo de 002.)

---

## 3. DTOs de Riot (no persistidos)

Los siguientes objetos viven solo en memoria y se devuelven como parte del response de `GET /api/profile`. Definidos como dataclasses inmutables en `services/riot_api/client.py` o como `BaseModel` en `schemas/profile.py` según convenga.

### `SummonerProfile`

| Campo | Tipo | Notas |
|-------|------|-------|
| `summoner_level` | `int` | Nivel de invocador |
| `region` | `str` | Eco de `riot_accounts.region` (no se vuelve a calcular) |

### `RankedEntry`

| Campo | Tipo | Notas |
|-------|------|-------|
| `queue_type` | `Literal["RANKED_SOLO_5x5", "RANKED_FLEX_SR"]` | |
| `tier` | `str` | "IRON", ..., "CHALLENGER" |
| `rank` | `str` | "I"-"IV" (vacío si tier es Master/Grandmaster/Challenger) |
| `league_points` | `int` | LP |
| `wins` | `int` | |
| `losses` | `int` | |

### `RankedStats`

| Campo | Tipo |
|-------|------|
| `solo_duo` | `RankedEntry \| None` |
| `flex` | `RankedEntry \| None` |

### `ChampionMastery`

| Campo | Tipo | Notas |
|-------|------|-------|
| `champion_id` | `int` | DataDragon ID |
| `champion_level` | `int` | |
| `champion_points` | `int` | |

### `MatchSummary`

| Campo | Tipo | Notas |
|-------|------|-------|
| `match_id` | `str` | |
| `played_at` | `datetime` | UTC |
| `duration_seconds` | `int` | |
| `champion_id` | `int` | Campeón jugado por el usuario |
| `kills` / `deaths` / `assists` | `int` | |
| `win` | `bool` | |
| `queue` | `str` | "RANKED_SOLO", "ARAM", etc. |

### `LoLStatsResponse` (envoltorio de respuesta)

```text
{
  "summoner": SummonerProfile | null + unavailable: bool,
  "ranked": RankedStats | null + unavailable: bool,
  "mastery": list[ChampionMastery] | null + unavailable: bool,
  "recent_matches": list[MatchSummary] | null + unavailable: bool
}
```

**Invariante de degradación**: si una sección falla en su llamada a Riot (HD-3), su valor se envía `null` con el flag `unavailable: true` correspondiente; el resto del payload es completo.

---

## 4. Estados y transiciones relevantes

### Estados de `RiotAccount`

```text
                +-------------------+
                |    no_existe      |  (usuario sin LoL vinculado)
                +-------------------+
                          |
                          | POST /api/profile/link/lol con Riot ID válido
                          v
                +-------------------+
                |     vinculada     |  (riot_accounts row presente)
                +-------------------+
                          |
                          | DELETE /api/profile/link/lol
                          | (solo si NO hay torneo activo)
                          v
                +-------------------+
                |    no_existe      |
                +-------------------+
```

No hay estado intermedio "vinculación pendiente": la operación es síncrona dentro del request.

### Estados de `User` relevantes a esta feature

```text
        +---------+    DELETE /api/profile/me     +-------------+
        | activo  | ----------------------------> | anonimizado |
        +---------+   (con confirmación válida y  +-------------+
                       sin torneo activo)
```

Una vez `deleted_at` está presente, no hay transición de vuelta a "activo".

---

## 5. Migración Alembic prevista

Migración nueva `add_avatar_and_riot_account.py`:

1. `ALTER TABLE users ADD COLUMN avatar_url VARCHAR(2048) NULL;`
2. `ALTER TABLE users ADD COLUMN deleted_at TIMESTAMPTZ NULL;`
3. `CREATE TABLE riot_accounts (...)` con las columnas y constraints anteriores; índices en `user_id` (UNIQUE) y `puuid` (UNIQUE).
4. Sin backfill: las columnas nuevas son nullable y los usuarios existentes tienen `avatar_url = NULL` y `deleted_at = NULL`.

`downgrade()` revierte ambos pasos.

---

## 6. Invariantes globales (testeables)

| ID | Invariante | Test que la valida |
|----|-----------|--------------------|
| INV-1 | `riot_accounts.user_id` es UNIQUE y FK válida hacia `users.id` | `test_riot_account_unique_per_user` |
| INV-2 | Ningún registro de `riot_accounts` referencia un `users` con `deleted_at` no nulo | `test_delete_account_removes_riot_account` |
| INV-3 | `users.avatar_url`, si presente, es una URL HTTP/HTTPS válida según `HttpUrl` | `test_update_avatar_rejects_invalid_url` |
| INV-4 | `users.nickname` es UNIQUE incluyendo filas anonimizadas; las filas anonimizadas usan el patrón `deleted-{8 chars}` que no choca con nicknames reales (regla de aplicación) | `test_delete_account_anonymized_nickname_does_not_collide` |
| INV-5 | Tras `DELETE /api/profile/me`, el `password_hash` no permite ningún login | `test_delete_account_blocks_future_login` |
| INV-6 | Tras cambio de contraseña, los refresh tokens del usuario distintos de la sesión actual quedan en `token_blacklist` | `test_change_password_blacklists_other_sessions` |
| INV-7 | `riot_accounts.puuid` es UNIQUE (no se puede vincular el mismo PUUID a dos usuarios) | `test_link_lol_rejects_duplicate_puuid` |
| INV-8 | `riot_accounts.region` ∈ whitelist | `test_link_lol_rejects_unknown_region` |

---

## Notas finales

- No hay cambios en `Tournament`, `Participant`, `Invitation`, `Match`, `Notification` ni `TokenBlacklist`. La feature solo **lee** algunas de esas tablas para evaluar bloqueos (`participants` JOIN `tournaments` por estado).
- La política "datos LoL en tiempo real, sin caché" implica que **ninguna tabla almacena niveles, ranked, maestrías ni partidas**. Toda esa información se obtiene de Riot en cada `GET /api/profile`.
