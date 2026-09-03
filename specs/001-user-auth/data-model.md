# Phase 1 — Data Model: Autenticación de usuarios

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md)

Entidades y reglas de validación extraídas de la spec y del stack fijado. Los tipos se expresan a nivel de dominio; el mapeo concreto a columnas SQLAlchemy ocurrirá durante la implementación (siempre vía TDD, Principio II).

---

## Entidad: `User`

Fuente de la entidad: spec §Key Entities "Usuario" + restricciones de `prompts/second/01-autenticacion.txt`.

| Campo | Tipo | Restricciones | Origen |
|-------|------|---------------|--------|
| `id` | UUID v4 | PK, generado en servidor. | Prompt: *"IDs de usuario en formato UUID v4"*. |
| `email` | string | Único, indexado, formato email válido (Pydantic `EmailStr`). | Spec FR-004, FR-001. |
| `nickname` | string | Único, indexado, sólo letras minúsculas/mayúsculas (ver D8). | Spec FR-002, FR-003, FR-005. |
| `password_hash` | string | No nulo; hash bcrypt via passlib. Nunca se almacena la contraseña en claro. | Spec FR-006, SC-007. |
| `failed_login_attempts` | int | ≥0, default 0. | D5 (aprobado por el humano). |
| `locked_until` | timestamp (UTC) \| null | null si la cuenta no está bloqueada por fuerza bruta. | D5 (aprobado). |
| `created_at` | timestamp (UTC) | No nulo, default `now()`. | Estándar. |

**Reglas de validación (aplicadas en backend):**

- `email`: formato válido (`EmailStr`); rechazo con 409 si colisiona (FR-004).
- `nickname`:
  - Si viene explícito: no vacío, sólo `[A-Za-z]+`, longitud razonable (1–32). Rechazo con 409 si colisiona (FR-005).
  - Si viene vacío/ausente: el servicio genera `user<5-dígitos>` hasta insertarlo sin colisión (D6). El cliente no ve error de colisión.
- `password`: longitud mínima 8 caracteres (prompt); no se imponen reglas de complejidad adicionales en esta versión.
- **No** se exponen `password_hash`, `failed_login_attempts` ni `locked_until` en ninguna respuesta.

**Transiciones de estado (rate limiting per-account — D5, aprobado):**

```
[unlocked]
  fail login                             --> failed_login_attempts += 1
  fail login (n >= 10 en ventana 15 min) --> [locked_until = now + 15 min]
  successful login                       --> failed_login_attempts = 0
                                             locked_until = null   (reset explicito)

[locked] (locked_until > now())
  any login attempt     --> rechazo con "Credenciales invalidas" (no se revela el lock, FR-008)
  locked_until <= now() --> [unlocked], failed_login_attempts = 0
```

---

## Entidad: `TokenBlacklist`

Fuente: prompt *"Blacklist de refresh tokens invalidados almacenada en base de datos"* + FR-014 (logout invalida sesión) + rotación de refresh token (D2).

| Campo | Tipo | Restricciones | Notas |
|-------|------|---------------|-------|
| `jti` | string (UUID) | PK. Identificador único del JWT (claim `jti`). | Cada refresh token se emite con un `jti` único. |
| `user_id` | UUID v4 | FK → `User.id`, indexado. | Permite invalidar todos los refresh tokens de un usuario si algún día se necesita (no en este plan). |
| `revoked_at` | timestamp (UTC) | No nulo, default `now()`. | Momento en que se invalidó. |
| `expires_at` | timestamp (UTC) | No nulo. | Copia de la expiración del token. Permite purga periódica (no se guardan tokens ya caducados eternamente). |

**Reglas de uso:**

- Tras un `POST /auth/refresh` exitoso: el `jti` del refresh token recibido pasa a `TokenBlacklist`; se emite un nuevo refresh token con nuevo `jti`.
- Tras un `POST /auth/logout`: el `jti` del refresh token actual pasa a `TokenBlacklist`; access y refresh cookies se borran con `Set-Cookie ... Max-Age=0`.
- En cada verificación de refresh token (antes de emitir nuevo access): comprobar que el `jti` **no** está en la blacklist. Si lo está ⇒ rechazo 401.
- **Purga**: job o tarea manual puede eliminar filas con `expires_at < now()` (opcional; no crítico para seguridad, sí para no acumular).

---

## Entidad auxiliar (no persistente): `Session (conceptual)`

La spec menciona `Sesión` como entidad, pero en esta implementación **no se persiste una tabla de sesiones**: el estado está en los JWTs firmados y en la blacklist de refresh tokens. La "sesión" es:

- Un access token vivo (≤15 min) + un refresh token vivo (≤7 días) no blacklisteado, ambos en cookies del cliente.
- Se considera **activa** si ambos están dentro de su TTL y el refresh no está blacklisted.
- Se considera **expirada** si el refresh ha caducado o el access ha caducado sin llamar a `/auth/refresh`.
- Se considera **invalidada por logout** si el refresh está en `TokenBlacklist`.

Esta decisión es coherente con el prompt (no hay mención a tabla de sesiones) y evita duplicar estado entre JWT y BBDD.

---

## Índices y constraints (PostgreSQL)

- `users.email` UNIQUE, índice btree.
- `users.nickname` UNIQUE, índice btree.
- `users.id` PK (UUID).
- `token_blacklist.jti` PK.
- `token_blacklist.user_id` índice btree (consultas por usuario si se requiere revocación masiva).
- `token_blacklist.expires_at` índice btree (purga por rango).

---

## Derivación a tests (Principio II)

Los tests se escriben **antes** que el código. Esquema de cobertura por entidad:

- **User — unit** (`tests/unit/test_security.py`, `test_auth_service.py`):
  - hash ≠ contraseña.
  - verificación correcta / incorrecta.
  - `generate_unique_nickname()` reintenta en colisión.
  - incremento de `failed_login_attempts` en fallo.
  - reset de `failed_login_attempts` y limpieza de `locked_until` en login correcto.
  - bloqueo cuando `failed_login_attempts >= 10` en ventana 15 min.
- **User — integration** (`tests/integration/test_auth_routes.py`):
  - duplicado de email ⇒ 409.
  - duplicado de nickname ⇒ 409.
  - registro sin nickname ⇒ 201 y nickname con formato `user\d{5}`.
  - login correcto ⇒ 200 con cookies HttpOnly.
  - login con email inexistente y login con password incorrecta devuelven exactamente la misma respuesta (status + body + tiempo comparable).
- **TokenBlacklist — unit** (`test_security.py`):
  - `jti` rechazado tras blacklist.
- **TokenBlacklist — integration** (`test_auth_routes.py`):
  - refresh rotado: el anterior queda inválido.
  - logout ⇒ refresh reutilizado rechazado.
