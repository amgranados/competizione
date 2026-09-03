# Phase 0 — Research: Autenticación de usuarios

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

Este documento consolida las decisiones técnicas impuestas por el humano (`prompts/second/01-autenticacion.txt`) y las complementa con: (a) justificación con fuentes (Constitución III), (b) auditoría CVE por dependencia (Constitución I, requiere supervisión humana antes de instalar), (c) mitigaciones para las restricciones de la spec, (d) gaps detectados entre spec y stack.

---

## D1. Stack general

- **Decision**: Backend Python 3.12 + FastAPI; Frontend React + Vite; PostgreSQL async con SQLAlchemy 2.x + Alembic; tests con pytest (backend) y Vitest (frontend).
- **Rationale**: Impuesto por el humano en el prompt. Constitución IV: no se cuestiona ni se sustituye. Pydantic v2 + FastAPI es el patrón idiomático para validación en FastAPI (fuente: docs oficiales FastAPI — *Pydantic v2 is the default since FastAPI 0.100*).
- **Alternatives considered**: No aplica (decisión humana fija).

## D2. Mecanismo de sesión — JWT access + refresh en cookies HttpOnly

- **Library**: **PyJWT** (decisión humana B tras la CVE audit; sustituye a python-jose).
- **Decision**: Access token (15 min) y refresh token (7 días), ambos JWT HS256 firmados y verificados con `PyJWT.encode(...)` / `PyJWT.decode(..., algorithms=["HS256"])` (lista explícita para rechazar `alg=none` y algoritmos asimétricos por confusión). Tokens enviados exclusivamente como cookies `HttpOnly; Secure; SameSite=lax`. Refresh token **rotación en cada uso** con blacklist persistente en PostgreSQL.
- **Rationale**:
  - Cookies HttpOnly satisfacen FR-012 (tokens no legibles por JS cliente). Fuente: OWASP Cross-Site Scripting Prevention — *"Cookies used for session management must be HttpOnly"*.
  - `SameSite=lax` mitiga CSRF en la mayoría de escenarios; `SameSite=strict` rompería el flujo de login con redirects desde emails. Fuente: OWASP CSRF Prevention Cheat Sheet.
  - HS256 (simétrico) es aceptable porque el backend es único y firma y verifica con la misma `SECRET_KEY`; no hay consumidor externo que requiera verificación con clave pública. Fuente: RFC 7518 §3.2.
  - Rotación de refresh token mitiga el impacto de un refresh token robado: si el atacante lo usa, el legítimo detecta al intentar refrescar con un token ya blacklisteado ⇒ flujo de alerta/sign-out. Fuente: OAuth 2.0 Security BCP — *"Refresh Token Rotation (Section 4.13)"*.
- **Alternatives considered**:
  - Sesión server-side opaca con cookie ⇒ simpler pero descartado por el humano.
  - JWT en `localStorage` ⇒ **rechazado explícitamente** en el prompt y violaría FR-012.

## D3. Hashing de contraseñas — bcrypt via passlib

- **Decision**: `passlib[bcrypt]` con `CryptContext(schemes=["bcrypt"], deprecated="auto")`, factor de coste por defecto (12).
- **Rationale**:
  - bcrypt sigue siendo aceptado por OWASP Password Storage Cheat Sheet (*"bcrypt with a work factor of 10 or more"*) y cumple FR-006 (hash no reversible).
  - passlib encapsula el hash con sal + verificación en tiempo constante.
- **Alternatives considered**:
  - **argon2id** (recomendación preferente actual de OWASP) ⇒ no elegido por el humano. Si se desea migrar después, passlib soporta `schemes=["argon2", "bcrypt"]` con `deprecated="auto"` y rehash al siguiente login correcto.

## D4. Rate limiting — slowapi, 5/min por IP en `POST /auth/login`

- **Decision**: `slowapi` con regla `@limiter.limit("5/minute")` sobre el endpoint de login. Clave de cubeta = IP del cliente (`get_remote_address`).
- **Rationale**: Prompt humano. slowapi se integra como middleware de FastAPI y cubre FR-018 (límite por origen agregado).
- **⚠️ Gap con la spec**: FR-017 pide un **límite por cuenta** (protege a una cuenta específica aunque el atacante rote IPs). Propuesta de complemento (ver D5); requiere tu OK.

## D5. Rate limiting per-account (aprobado por el humano)

- **Decision**: **APROBADA**. En `User`: `failed_login_attempts: int` (default 0) y `locked_until: datetime | null`. Lógica:
  - Cada intento fallido incrementa el contador.
  - Si `failed_login_attempts >= 10` en los últimos 15 min ⇒ `locked_until = now + 15 min`; todos los intentos de login devuelven `"Credenciales inválidas"` sin revelar el bloqueo (FR-008).
  - **Un login correcto resetea el contador a 0 y limpia `locked_until`** (confirmación humana explícita).
  - Un `locked_until` caducado se ignora y vuelve a empezar el conteo en el próximo intento fallido.
- **Rationale**: Cumple FR-017 sin introducir dependencias nuevas. Umbrales 10/15min/15min alineados con la orientación OWASP ASVS V2.2.1 (*"rate limit and progressive delays after failed authentication attempts"*).
- **Alternatives considered**: Usar slowapi con clave `email` ⇒ rechazado porque slowapi ejecuta el rate limit **antes** del handler y no conoce aún el email (viene en el body).

## D6. Nickname auto-generado (FR-003)

- **Decision**: Cuando el usuario no proporciona `nickname`, `auth_service.generate_unique_nickname()` genera `f"user{random.randint(10000, 99999)}"` y reintenta hasta que la inserción tenga éxito (unicidad a nivel de columna en PostgreSQL, `IntegrityError` ⇒ reintento). Máximo 10 intentos; si todos fallan (~improbable con 90 000 valores posibles pero muy pocos usuarios en el estado inicial), se devuelve error de servidor.
- **Rationale**: Cumple FR-003 y la edge case *"colisión de nickname auto-generado"* documentada en la spec. La atomicidad la garantiza la BBDD, no el chequeo previo en Python (evita TOCTOU).

## D7. Mitigación de timing oracle en `/auth/login`

- **Decision**: Cuando `email` no existe en BBDD, ejecutar un hash dummy (`passlib.CryptContext.dummy_verify()` o equivalente: un `verify_password("", DUMMY_HASH)` precomputado) antes de devolver el mismo error `"Credenciales inválidas"`.
- **Rationale**: FR-008 y SC-003 exigen respuestas **indistinguibles por tiempo**. Sin el hash dummy, el backend responde significativamente más rápido cuando el email no existe, lo que permite enumerar cuentas por timing. Fuente: OWASP Authentication Cheat Sheet — *"Authentication responses should always return the same HTTP response (same status, same body, same timing) regardless of whether the user exists"*.

## D8. Validación de entradas

- **Decision**: Pydantic v2 schemas en `backend/app/schemas/auth.py`:
  - `RegisterRequest`: `email: EmailStr`, `password: str (min_length=8)`, `nickname: Annotated[str, StringConstraints(pattern=r"^[A-Za-z]+$")] | None = None`.
  - `LoginRequest`: `email: EmailStr`, `password: str`.
- **Rationale**: La spec permite nickname con minúsculas y mayúsculas (FR-002) sin especificar otros caracteres; se usa el conjunto mínimo declarado. Si se requiere admitir dígitos/guiones, revisar la spec.

## D9. CORS

- **Decision**: `CORSMiddleware` con `allow_origins=[FRONTEND_ORIGIN]`, `allow_credentials=True`, `allow_methods=["GET", "POST"]`, `allow_headers=["Content-Type"]`.
- **Rationale**: `credentials: "include"` del frontend exige `allow_credentials=True` y un `allow_origins` **explícito** (no `*`). Restringir métodos/headers reduce superficie.

## D10. TDD Workflow (Principio II)

- **Decision**: Por cada FR se escribe primero el test (Red), luego la implementación mínima para que pase (Green), luego refactor manteniendo verde.
- **Mapeo FR → archivo de test inicial**:
  - FR-001, FR-002, FR-003, FR-004, FR-005 ⇒ `backend/tests/integration/test_auth_routes.py::test_register_*` + `tests/unit/test_auth_service.py::test_generate_unique_nickname`.
  - FR-006 ⇒ `tests/unit/test_security.py::test_password_is_hashed_and_verifiable`.
  - FR-007, FR-008 ⇒ `tests/integration/test_auth_routes.py::test_login_*`, incluyendo `test_login_same_response_for_unknown_email_and_wrong_password` (verifica status, body y latencia similar).
  - FR-009, FR-010, FR-011 ⇒ `test_auth_routes.py::test_refresh_*`.
  - FR-012 ⇒ `test_auth_routes.py::test_tokens_set_as_httponly_cookies` (inspecciona la cabecera `Set-Cookie`).
  - FR-013, FR-014 ⇒ `test_auth_routes.py::test_logout_*` y `test_reused_refresh_token_after_logout_is_rejected`.
  - FR-015, FR-016 ⇒ `test_auth_routes.py::test_protected_routes_require_auth`.
  - FR-017, FR-018, FR-019 ⇒ `test_auth_routes.py::test_ip_rate_limit_blocks_6th_attempt_in_a_minute` y (si se aprueba D5) `test_account_lockout_after_n_failed_attempts`.
- Front: `frontend/tests/integration/Login.test.jsx`, `Register.test.jsx`, `ProtectedRoute.test.jsx` con MSW mockeando `/auth/*`.

---

## CVE Audit (Principio I — requiere supervisión humana antes de instalar)

Fuentes consultadas: NVD (nvd.nist.gov), GitHub Security Advisory (github.com/advisories), OSV (osv.dev), PyPA advisory DB. La auditoría se hace antes de ejecutar `pip install`. **No se instala nada sin aprobación humana.**

### Backend

| Paquete | Versión recomendada | Hallazgos | Acción propuesta |
|---------|---------------------|-----------|------------------|
| `fastapi` | ≥0.111 | Sin CVEs críticos abiertos al conocimiento del asistente. | OK para instalar tras tu aprobación. |
| `uvicorn` | ≥0.30 | Sin CVEs críticos abiertos. | OK. |
| `sqlalchemy` | ≥2.0.30 | Sin CVEs críticos abiertos; la rama 1.x tenía CVEs menores resueltos en 2.x. | OK. |
| `alembic` | ≥1.13 | Sin CVEs críticos. | OK. |
| `pydantic` | ≥2.7 | Sin CVEs críticos. | OK. |
| `pydantic-settings` | ≥2.2 | Sin CVEs críticos. | OK. |
| ~~`python-jose[cryptography]`~~ | **descartado** | CVE-2024-33663/33664 + mantenimiento reducido. | **RESUELTO**: humano eligió sustituir por `PyJWT`. No se instalará python-jose. |
| `PyJWT` | ≥2.9 | Sin CVEs críticos abiertos conocidos. Mantenido por Auth0. Tests propios deben verificar rechazo de `alg=none` y `alg` no permitidos. | OK. |
| `passlib[bcrypt]` | ≥1.7.4 | No hay CVEs críticos publicados en passlib. Nota: `passlib` ha reducido cadencia de releases; `bcrypt` Python package (≥4.x) sigue mantenido. | OK con observación (monitorizar mantenimiento). |
| `python-multipart` | **≥0.0.9** | **CVE-2024-24762** (ReDoS en parsing de `Content-Type`) parcheada en **0.0.7**. | OK siempre que fijemos `python-multipart>=0.0.9` en `requirements.txt`. |
| `slowapi` | ≥0.1.9 | Sin CVEs críticos conocidos. | OK. |

### Frontend

| Paquete | Versión recomendada | Hallazgos | Acción propuesta |
|---------|---------------------|-----------|------------------|
| `react`, `react-dom` | ≥18.3 | Sin CVEs críticos. | OK. |
| `react-router-dom` | v6 (≥6.22) | Hubo advisories menores (GHSA-5j4c-2p4r-qv9m 2024 afectaba v6 < 6.22 en cierto edge case de rutas). Actualizar al último parche. | OK con pin ≥6.22. |
| `vite` | ≥5.2 | Advisory GHSA-vg6x-rcgg-rjx6 (2024) dev-server SSRF; sólo afecta al dev-server en red no confiable. No corre en producción. | OK para desarrollo; no exponer el dev-server. |
| `vitest` | ≥1.6 | Sin CVEs críticos. | OK. |
| `@testing-library/react`, `-user-event` | últimos | Sin CVEs críticos. | OK. |
| `msw` | ≥2.x | Sin CVEs críticos. | OK. |

### Resumen — decisiones humanas aplicadas

1. **RESUELTO**: `python-jose` sustituido por `PyJWT` (decisión humana, opción B).
2. **RESUELTO**: `python-multipart>=0.0.9` y `react-router-dom>=6.22` aceptadas como pins mínimos.
3. El resto de paquetes puede instalarse en sus versiones actuales sin observaciones de seguridad.

Con esto, el gate de Constitución I (Cybersecurity) **PASA** y la instalación real de dependencias queda autorizada para la fase de implementación.

---

## Post-Design Re-check (tras Fase 1)

Tras generar `data-model.md`, `contracts/auth.openapi.yaml` y los diagramas PlantUML, se verifica:

- **No se han añadido dependencias nuevas.** `User` (con `failed_login_attempts` + `locked_until` ya aprobados) y `TokenBlacklist` se implementan con SQLAlchemy.
- **TDD sigue siendo viable**: cada endpoint del OpenAPI tiene un test asociado en D10.
- **Diagramas en PlantUML** (Principio III): `contracts/auth-flow.puml`, `contracts/session-lifecycle.puml`.
- **Sin violaciones** en el Constitution Check.

Gate **PASA**. Listo para `/speckit.tasks`.
