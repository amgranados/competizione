# Quickstart — 001 User Auth

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md) · **Data model**: [data-model.md](./data-model.md)

Puesta en marcha del entorno de desarrollo para la feature de autenticación. La auditoría CVE (`research.md § CVE Audit`) ha sido aprobada por el humano: `python-jose` sustituido por **PyJWT**; `python-multipart>=0.0.9`; `react-router-dom>=6.22`.

---

## Prerrequisitos

- Python **3.12+**.
- Node **20 LTS+**.
- PostgreSQL **15+** corriendo localmente (puerto 5432) o alcanzable por `DATABASE_URL`.
- Git (ya usado).
- Capacidad de establecer HTTPS o, en dev, `secure_cookies=False` **solo en desarrollo** (ver sección "Desarrollo sin HTTPS").

## Variables de entorno (backend)

Crear `backend/.env` a partir de `backend/.env.example` (el `.env` NO debe commitearse):

```dotenv
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/competizione
SECRET_KEY=<cadena aleatoria >= 32 caracteres>
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
FRONTEND_ORIGIN=http://localhost:5173
```

Generar un `SECRET_KEY` con `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

## Variables de entorno (frontend)

Crear `frontend/.env.development` con:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
```

El frontend usa `fetch` nativo con `credentials: "include"`.

---

## Setup backend (TDD primero — Principio II)

Tras aprobación humana de la CVE audit:

1. Crear entorno virtual y dependencias:

   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate      # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Preparar base de datos (Alembic):

   ```bash
   alembic upgrade head
   ```

   Las migraciones aún no existen; se generan como parte del flujo TDD (primero un test que inserta un `User`, luego el modelo, luego `alembic revision --autogenerate`).

3. Ejecutar tests (deben existir antes que el código productivo):

   ```bash
   pytest -q
   ```

4. Arrancar servidor sólo tras tests en verde:

   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

## Setup frontend (TDD primero)

1. Instalar dependencias:

   ```bash
   cd frontend
   npm install
   ```

2. Ejecutar tests:

   ```bash
   npm run test       # Vitest en modo watch
   # o
   npm run test:run   # una sola pasada
   ```

3. Arrancar dev server:

   ```bash
   npm run dev        # http://localhost:5173
   ```

---

## Flujo TDD por FR (resumen)

Extracto de `research.md § D10`. Cada ciclo Red-Green-Refactor empieza por el fichero de test y luego baja al código:

1. `tests/integration/test_auth_routes.py::test_register_with_email_password_creates_account` ⇒ implementar `POST /auth/register` mínimo.
2. `tests/unit/test_auth_service.py::test_generate_unique_nickname_retries_on_collision` ⇒ implementar `generate_unique_nickname`.
3. `tests/integration/test_auth_routes.py::test_login_same_response_for_unknown_email_and_wrong_password` ⇒ implementar verificación con dummy hash (anti-timing).
4. `tests/integration/test_auth_routes.py::test_tokens_set_as_httponly_cookies` ⇒ configurar `Set-Cookie` en respuestas.
5. `tests/integration/test_auth_routes.py::test_refresh_rotates_and_blacklists_old_token` ⇒ implementar rotación + blacklist.
6. `tests/integration/test_auth_routes.py::test_logout_invalidates_refresh_token` ⇒ implementar logout.
7. `tests/integration/test_auth_routes.py::test_protected_route_requires_authentication` ⇒ middleware/dependency de auth.
8. `tests/integration/test_auth_routes.py::test_login_rate_limit_returns_429_after_5_attempts_per_minute` ⇒ slowapi.
9. `tests/integration/test_auth_routes.py::test_account_locks_after_10_failed_attempts_in_15_minutes` y `test_successful_login_resets_failed_attempts_counter` ⇒ contador per-account (D5 aprobado).
10. Frontend: `tests/integration/Login.test.jsx`, `Register.test.jsx`, `ProtectedRoute.test.jsx` con MSW ⇒ componentes y `useAuth`.

---

## Comprobación manual (después del primer MVP verde)

1. `POST /auth/register` con email + password ⇒ 201 con cookies `access_token` y `refresh_token` en DevTools > Application > Cookies (ambas marcadas HttpOnly ✅).
2. Navegador NO puede leer `document.cookie` sobre esas cookies (prueba de FR-012).
3. `POST /auth/login` con password errónea ⇒ respuesta 401 con `{"detail":"Credenciales inválidas"}`.
4. `POST /auth/login` con email inexistente ⇒ misma respuesta exacta y latencia similar a (3).
5. Acceder a ruta protegida sin cookies ⇒ 401.
6. Esperar 15 min (o reducir `ACCESS_TOKEN_EXPIRE_MINUTES` en `.env` de dev a 1) ⇒ llamar a `/auth/refresh` ⇒ cookies rotadas.
7. Llamar a `/auth/logout` y reintentar la ruta protegida con las cookies viejas ⇒ 401.
8. 6 llamadas a `/auth/login` en <60 s desde la misma IP ⇒ la 6.ª devuelve 429.

## Desarrollo sin HTTPS

En local, `Secure=True` bloquea cookies sobre `http://localhost` en algunos navegadores. Opciones:

- Preferida: correr detrás de un proxy HTTPS local (mkcert + Caddy/Traefik).
- Alternativa: marcar `secure=False` **sólo** cuando `settings.env == "development"` y con aviso explícito en los logs. No permitir esta rama en producción.

---

## Próximos pasos

- Ejecutar `/speckit.tasks` para generar `tasks.md` con el plan de trabajo TDD priorizado por user stories (P1 → P2 → P3).
