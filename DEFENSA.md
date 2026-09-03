# 🎯 Guía de defensa — Competizione (5 minutos)

> Plataforma web para organizar torneos 1v1 de League of Legends entre amigos, con integración real con la API de Riot Games.

---

## 1. Discurso de apertura (30 segundos)

> "Competizione es una aplicación full-stack para crear y gestionar torneos de League of Legends. Un usuario se registra, vincula su cuenta de Riot, crea un torneo en formato liga o eliminación directa, invita a sus amigos, y la app genera el calendario, los códigos de torneo oficiales de Riot para crear las lobbies en el juego, la clasificación y el cuadro. Backend en **FastAPI + PostgreSQL**, frontend en **React + Vite**, todo desplegable con **Docker Compose**."

---

## 2. Stack técnico (tenlo memorizado)

| Capa | Tecnología |
|---|---|
| Backend | Python, FastAPI (async), SQLAlchemy 2 async, Alembic (migraciones) |
| Base de datos | PostgreSQL |
| Frontend | React + Vite, fetch propio (sin Redux: Context + hooks) |
| Auth | JWT en cookies httpOnly (access 15 min + refresh 7 días con blacklist) |
| Integración externa | API de Riot Games (httpx async) + Data Dragon para assets |
| Infra | Docker Compose (dev y prod), Nginx sirviendo el frontend |
| Calidad | pytest (backend), tests frontend, pre-commit + gitleaks (anti-secretos), CI en GitHub Actions |
| Metodología | Spec-driven: cada feature tiene su carpeta en `specs/` (001-auth … 006-audit) |

---

## 3. Funcionalidades del sistema (lista completa)

1. **Autenticación** — registro, login, logout, refresh de sesión, política de contraseñas, rate-limiting de intentos.
2. **Perfil** — editar nickname/datos, eliminar cuenta, **vincular cuenta de Riot** (Riot ID → PUUID) y ver stats reales: nivel de invocador, icono de perfil, **ranked Solo/Dúo y Flexible** (tier, división, LP, winrate), maestría de campeones e **historial de las últimas partidas** (campeón, KDA, victoria/derrota, duración). Todo visible también en el perfil público de otros usuarios.
3. **Amigos** — buscar usuarios, enviar/aceptar/rechazar solicitudes, ver perfiles de otros usuarios.
4. **Torneos** — crear (formato **liga round-robin** o **eliminación directa**), registro abierto o por invitación (con caducidad de 48 h), el organizador puede participar, arrancar torneo → se genera el calendario/cuadro automáticamente.
5. **Partidas** — filas de partido en calendario y bracket, registro manual de resultados, avance automático del ganador de ronda, cierre de ronda y finalización automática del torneo.
6. **Clasificación y cuadro** — tabla de standings (liga) y bracket visual (eliminación).
7. **Códigos de torneo reales de Riot** — cada partida recibe un código oficial que los jugadores meten en el cliente de LoL para crear la lobby (Tournament-Stub-V5).
8. **Notificaciones** — campana con notificaciones persistentes (invitación recibida, resultado registrado, solicitud de amistad…), marcar como leídas.
9. **Dashboard** — resumen del usuario: sus torneos, próximas partidas, feed de actividad de amigos, tarjetas de estadísticas.
10. **Feed de actividad** — eventos de tus amigos (creó torneo, ganó partida…), con control de acceso: no enlaza torneos a los que no tienes acceso.

---

## 4. Preguntas probables y cómo responderlas

### ❓ "¿Cómo llegan las notificaciones a los usuarios?"
> "Por **polling**. Las notificaciones se **persisten en base de datos** (tabla `notifications`): cuando ocurre un evento — te invitan a un torneo, se registra un resultado, te llega una solicitud de amistad — el servicio correspondiente inserta la notificación en la misma transacción (en bloque con `add_all` si son varias, para eficiencia). El frontend tiene un hook genérico `usePolling` que consulta `GET /notifications` cada 10 segundos desde un Context global y actualiza la campana. Elegí polling frente a WebSockets porque para esta escala es más simple, sin estado en el servidor, y la latencia de 10 s es aceptable para notificaciones de torneo. La migración a WebSockets/SSE sería el siguiente paso natural y solo afectaría a la capa de transporte, no al modelo."

### ❓ "¿Cómo está configurada/integrada la API de Riot?"
> Puntos clave (ver detalle en sección 5):
> 1. La key va en la variable de entorno `RIOT_API_KEY`, **nunca en el código** (gitleaks lo verifica en pre-commit).
> 2. Hay un **Protocol** (interfaz) `RiotAPIClient` con dos implementaciones: `HttpRiotAPIClient` (real, con httpx async) y `MockRiotAPIClient` (sin key, para dev/tests). Una factoría decide cuál usar; **en producción sin key la app falla al arrancar** en vez de servir datos falsos en silencio.
> 3. La autenticación con Riot va en la cabecera `X-Riot-Token`.
> 4. Los errores se mapean a dos excepciones de dominio: 4xx → `RiotIdentityError`, 5xx/timeout → `RiotUnavailableError`, y la app **degrada con elegancia**: si Riot cae, el torneo sigue con códigos locales.

### ❓ "¿Cómo funciona la autenticación? ¿Por qué cookies y no localStorage?"
> "JWT de acceso de 15 minutos + token de refresh de 7 días, ambos en **cookies httpOnly, SameSite=Lax y Secure en producción**. httpOnly evita que un XSS robe el token (localStorage es legible por JavaScript). Al hacer logout o refresh, el token usado se mete en una **blacklist** en BD para que no se pueda reutilizar. Además: política de contraseñas con hash bcrypt, rate-limiting por IP en login (slowapi) con `X-Forwarded-For` solo confiado desde el proxy configurado, y CORS restringido al origen del frontend."

### ❓ "¿Cómo se genera el calendario / el cuadro?"
> "Al arrancar el torneo, `calendar_service` genera todas las partidas: en **round-robin**, todos contra todos por jornadas; en **eliminación directa** se construye el bracket con *byes* si el número de jugadores no es potencia de 2. Cuando todos los resultados de una ronda están registrados, se cierra la ronda, los ganadores avanzan a la siguiente (generando sus códigos de Riot) y el torneo se finaliza automáticamente al decidirse la final."

### ❓ "¿Quién registra los resultados? ¿Se verifican con Riot?"
> "Actualmente el resultado lo registra manualmente el organizador (con guardas de autorización y de estado). La verificación automática está **preparada pero diferida**: los códigos de torneo de Riot llevan como `metadata` el id interno de la partida, y al registrar el provider se da una **callback URL** a la que Riot enviaría el resultado real de cada partida — con una key de producción bastaría implementar ese endpoint para correlacionar y verificar."

### ❓ "¿Cómo probaste la aplicación?"
> "Tests de backend con pytest sobre los servicios y rutas (con el mock de Riot para no depender de la red), tests de frontend, y una iteración completa (006) dedicada a **remediar una auditoría**: los commits referencian los hallazgos (L-02 escapado de URLs, I-05 inserciones en bloque, M-04 cabeceras de seguridad, etc.)."

### ❓ "¿Cómo se despliega?"
> "Docker Compose con tres servicios: Postgres, backend (las migraciones Alembic se aplican en el entrypoint) y frontend compilado servido por Nginx. Hay un `docker-compose.prod.yml` con perfil de producción: HTTPS detrás de reverse proxy, cookies Secure, HSTS, docs de la API (`/docs`) desactivadas, y secretos obligatorios sin valores por defecto."

### ❓ "¿Qué pasa si la API de Riot está caída?"
> "Degradación elegante: el linking de cuenta y las stats devuelven un error claro al usuario (503), pero los torneos **nunca se bloquean** — si no se pueden pedir códigos a Riot, las partidas conservan un código local de respaldo y el torneo continúa."

### ❓ "¿Qué mejorarías / próximos pasos?"
> "WebSockets para notificaciones en tiempo real, verificación automática de resultados vía el callback de Riot (ya preparado con la metadata), torneos por equipos (el cliente ya soporta `team_size`), y doble eliminación."

---

## 5. La API de Riot en detalle (apartado a recalcar ⭐)

### Configuración
- **Key** en `.env` → `RIOT_API_KEY` (las dev keys caducan cada 24 h: **regenera la tuya en developer.riotgames.com antes de la demo**).
- Variables extra: `RIOT_TOURNAMENT_REGION` (EUW) y `RIOT_TOURNAMENT_CALLBACK_URL`.
- Patrón **Strategy/factoría**: `get_riot_api_client()` devuelve el cliente HTTP real si hay key, el Mock si no (solo en dev/test; en producción aborta el arranque).

### Endpoints de Riot que se consumen
| Uso | Endpoint | Host |
|---|---|---|
| Vincular cuenta (Riot ID → PUUID) | `account/v1/accounts/by-riot-id` | continental (`europe.api.riotgames.com`) |
| Nivel e icono | `summoner/v4/summoners/by-puuid` | plataforma (`euw1...`) |
| Ranked Solo/Flex | `league/v4/entries/by-puuid` | plataforma |
| Maestría de campeones | `champion-mastery/v4` | plataforma |
| Historial de partidas | `match/v5/matches` (ids + detalle) | continental |
| Provider + torneo + **códigos de partida** | `tournament-stub/v5` (providers / tournaments / codes / lobby-events) | siempre `americas` |

> 💡 Las 4 llamadas de stats del perfil (summoner, mastery, ranked, matches) se lanzan **en paralelo** con `asyncio.gather`, y cada sección degrada por separado: si una falla, las demás se muestran igualmente (HD-3).

> 💡 Detalle que impresiona: Riot tiene **dos tipos de host** — continentales (europe/americas/asia) para account y match, y de plataforma (EUW1, NA1…) para summoner/league/mastery — y la Tournament API se sirve **siempre desde americas**. El cliente lo gestiona con helpers `_regional_host` / `_platform_host`.

### Flujo de códigos de torneo (Tournament-Stub-V5)
1. `POST /providers` → registra la app como organizadora (1 vez, con callback URL) → `providerId`.
2. `POST /tournaments` → contenedor lógico del torneo en Riot → `tournamentId` (ambos ids se **persisten** para no re-registrar).
3. `POST /codes` → un código por partida (`tournamentId` y `count` como query params). Parámetros exactos que envía la app en el body:
   - `teamSize: 1` (partidas 1v1)
   - `mapType: "SUMMONERS_RIFT"`
   - `pickType: "TOURNAMENT_DRAFT"`
   - `spectatorType: "ALL"`
   - `enoughPlayers: false`
   - `allowedParticipants`: los PUUIDs de los **dos** jugadores — solo se envía si ambos tienen cuenta Riot vinculada; si no, se omite
   - `metadata`: el UUID interno de la `Match` (correlaciona el callback de resultados de Riot con la partida en BD)
4. El jugador introduce el código en el cliente de LoL y se crea la lobby con esas reglas.

*(El "stub" es el sandbox oficial 1:1 de la Tournament API real — Riot solo da la API de producción a apps aprobadas; la migración es cambiar la URL base.)*

---

## 6. Apartados que debes recalcar

1. **Integración real con Riot** — no es una app CRUD: códigos de torneo oficiales, stats reales, manejo de regiones y resiliencia ante caídas.
2. **Seguridad trabajada** (iteración 006 de auditoría): cookies httpOnly, blacklist de tokens, rate-limiting con `X-Forwarded-For` confiable, cabeceras de seguridad (CSP, HSTS, X-Frame-Options), gitleaks anti-secretos, docs desactivadas en prod, fail-fast si falta la key en prod.
3. **Arquitectura por capas**: rutas (HTTP) → servicios (lógica de negocio + excepciones de dominio) → modelos (SQLAlchemy). Las rutas no tocan la BD directamente.
4. **Metodología spec-driven**: 6 iteraciones documentadas en `specs/` con requisitos funcionales numerados (FR-040…), trazables en el código.
5. **Testabilidad por diseño**: el Protocol de Riot permite testear toda la lógica sin red.
6. **Dev/prod parity con Docker**: misma imagen, distinta config por entorno vía `.env`.

---

## 7. Checklist pre-demo (¡hazlo antes de entrar!)

- [ ] **Regenerar la `RIOT_API_KEY`** en developer.riotgames.com (caduca cada 24 h) y ponerla en `.env`.
- [ ] `docker compose up` levantado y probado: login, crear torneo, arrancar, ver código de partida.
- [ ] Tener dos usuarios de prueba con cuentas de Riot vinculadas (para enseñar invitación + notificación en vivo: dos navegadores).
- [ ] Tener un torneo ya finalizado para enseñar standings/bracket sin esperar.
- [ ] Si la demo en vivo falla: el Mock de Riot funciona sin key — puedes quitar la key del `.env` y todo sigue funcionando (¡y eso también es un punto a tu favor: resiliencia!).

---

## 8. Frases de cierre si te sobra tiempo

- "El diseño está pensado para evolucionar: pasar del stub de Riot a la Tournament API real es cambiar una URL; pasar de polling a WebSockets no toca el modelo de datos."
- "Cada decisión de seguridad responde a un hallazgo concreto de la auditoría de la iteración 006, trazable en los commits."
