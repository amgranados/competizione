# Feature Specification: Autenticación de usuarios

**Feature Branch**: `001-user-auth`
**Created**: 2026-04-23
**Status**: Draft
**Input**: User description (`prompts/first/01-autenticacion.txt`): registro con email/contraseña y nickname opcional; login con mensaje genérico ante error; sesión persistente con renovación automática; logout explícito; protección de todas las rutas excepto inicio y registro; límite de intentos contra fuerza bruta. Los tokens de sesión no deben ser accesibles desde el navegador, y los mensajes de error no deben distinguir entre email y contraseña incorrectos.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registro e inicio de sesión con credenciales propias (Priority: P1)

Un visitante quiere empezar a usar la aplicación. Crea una cuenta proporcionando un email y una contraseña (y opcionalmente un nickname). Después, usa esas credenciales para iniciar sesión y acceder a la aplicación.

**Why this priority**: Sin registro y login no hay autenticación. Es el flujo mínimo viable; cualquier otra funcionalidad del feature depende de que exista una cuenta y de poder iniciar sesión con ella.

**Independent Test**: Validable de extremo a extremo usando sólo las pantallas de registro y login: completar el registro de un usuario nuevo y, a continuación, iniciar sesión con sus credenciales, obteniendo acceso a la zona autenticada.

**Acceptance Scenarios**:

1. **Given** un visitante sin cuenta, **When** envía el formulario de registro con email válido, contraseña válida y sin nickname, **Then** el sistema crea la cuenta, le asigna un nickname generado con el formato `user<5-dígitos>` y el usuario queda autenticado o puede iniciar sesión inmediatamente.
2. **Given** un visitante sin cuenta, **When** envía el formulario de registro con email válido, contraseña válida y un nickname que combina mayúsculas y minúsculas, **Then** el sistema crea la cuenta preservando el nickname tal como lo introdujo.
3. **Given** un email ya registrado, **When** otro visitante intenta registrarse con ese mismo email, **Then** el sistema rechaza el registro e informa que el email no está disponible.
4. **Given** un nickname ya en uso, **When** otro visitante intenta registrarse con ese mismo nickname, **Then** el sistema rechaza el registro e informa que el nickname no está disponible.
5. **Given** un usuario registrado, **When** inicia sesión con email y contraseña correctos, **Then** el sistema lo autentica y le da acceso a las rutas protegidas.
6. **Given** un usuario registrado, **When** introduce credenciales incorrectas (email inexistente o contraseña errónea), **Then** el sistema muestra exactamente el mismo mensaje genérico de error en ambos casos, sin revelar cuál es el motivo.

---

### User Story 2 - Protección de rutas de la aplicación (Priority: P1)

Una persona intenta acceder a cualquier ruta de la aplicación que no sea la de inicio o la de registro. La aplicación sólo le permite continuar si está autenticada; en caso contrario, la redirige a la pantalla de inicio de sesión.

**Why this priority**: La razón de ser de la autenticación es restringir el acceso a los datos sensibles. Sin protección de rutas, el login no aporta valor real.

**Independent Test**: Intentar abrir una URL protegida sin haber iniciado sesión y verificar que la aplicación impide el acceso; repetir la misma URL con una sesión activa y verificar que el acceso se concede.

**Acceptance Scenarios**:

1. **Given** un visitante sin sesión activa, **When** intenta acceder a una ruta protegida cualquiera, **Then** el sistema impide la entrada y lo redirige a la pantalla de inicio de sesión.
2. **Given** un visitante sin sesión activa, **When** accede a la ruta de inicio o a la de registro, **Then** el sistema se lo permite sin pedir autenticación.
3. **Given** un usuario autenticado, **When** navega a cualquier ruta protegida, **Then** el sistema le da acceso normalmente.

---

### User Story 3 - Sesión persistente con renovación automática (Priority: P2)

Un usuario que ya inició sesión cierra la pestaña y vuelve más tarde, o sigue usando la aplicación durante un rato largo. No tiene que volver a introducir sus credenciales: su sesión se mantiene entre visitas y se renueva automáticamente mientras esté activo.

**Why this priority**: Es una mejora importante de experiencia — si cada visita requiriese nuevo login, el producto sería frustrante —, pero el flujo de autenticación funciona sin ella.

**Independent Test**: Iniciar sesión, cerrar el navegador, volver a abrir la aplicación y verificar que se accede directamente a la zona autenticada. En una sesión larga, comprobar que el usuario no es expulsado mientras continúa interactuando.

**Acceptance Scenarios**:

1. **Given** un usuario que inició sesión y cerró el navegador, **When** vuelve a abrir la aplicación dentro del periodo de validez de la sesión, **Then** accede a las rutas protegidas sin volver a autenticarse.
2. **Given** un usuario con sesión activa que lleva interactuando continuamente un tiempo prolongado, **When** realiza cualquier acción autenticada, **Then** la sesión se renueva de forma transparente sin cortar su actividad.
3. **Given** un usuario cuya sesión ha expirado por inactividad, **When** intenta acceder a una ruta protegida, **Then** el sistema le pide iniciar sesión de nuevo.

---

### User Story 4 - Cierre de sesión explícito (Priority: P2)

Un usuario autenticado pulsa la opción de cerrar sesión. A partir de ese momento, ni él ni nadie que reutilice las cookies/tokens de esa sesión puede acceder a rutas protegidas con esa sesión.

**Why this priority**: Es una necesidad clara de control del usuario sobre su propia cuenta, especialmente en equipos compartidos, pero el MVP de autenticación puede demostrarse sin ella.

**Independent Test**: Iniciar sesión, pulsar logout y comprobar inmediatamente que al intentar acceder a una ruta protegida se pide nuevo login, incluso reutilizando el mismo token/cookie anterior.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado, **When** pulsa la opción de cerrar sesión, **Then** el sistema invalida su sesión y lo devuelve a la pantalla pública.
2. **Given** una sesión recién cerrada, **When** se reutiliza el mismo token/cookie que tenía antes del logout para intentar acceder a una ruta protegida, **Then** el sistema rechaza la petición como no autenticada.

---

### User Story 5 - Protección contra ataques de fuerza bruta (Priority: P3)

Un atacante intenta adivinar la contraseña de un usuario probando muchas combinaciones. El sistema detecta el patrón y bloquea temporalmente los intentos, impidiendo que siga probando.

**Why this priority**: Es crítico para la seguridad a medio plazo, pero el flujo funcional de autenticación existe y se puede probar sin esta capa: es hardening sobre un login ya funcional.

**Independent Test**: Ejecutar un número elevado de intentos de login fallidos contra una misma cuenta en poco tiempo y verificar que, a partir de cierto umbral, el sistema rechaza los nuevos intentos durante una ventana temporal, aunque la contraseña sea correcta.

**Acceptance Scenarios**:

1. **Given** una cuenta válida, **When** se realizan varios intentos de login fallidos consecutivos por encima del umbral configurado, **Then** el sistema bloquea temporalmente los siguientes intentos para esa cuenta/origen.
2. **Given** una cuenta bloqueada temporalmente, **When** transcurre la ventana de bloqueo sin nuevos intentos, **Then** el sistema permite reintentar el login con normalidad.
3. **Given** intentos repetidos y fallidos contra distintos usuarios desde una misma procedencia, **When** se supera el umbral global, **Then** el sistema limita también los intentos desde esa procedencia.

---

### Edge Cases

- Dos registros concurrentes intentan reservar el mismo email o el mismo nickname en el mismo instante: sólo uno debe completarse y el otro falla con el mensaje de duplicado.
- El nickname aleatorio auto-generado (`user<5-dígitos>`) colisiona con uno ya existente: el sistema debe reintentar hasta obtener uno libre, sin exponer el conflicto al usuario.
- Un usuario manipula manualmente la cookie/token de sesión (la modifica o la copia de otra cuenta): el sistema debe tratarla como no autenticada.
- Un usuario con sesión válida hace logout mientras otra pestaña sigue usando la misma sesión: todas las pestañas deben perder el acceso a rutas protegidas.
- Un usuario intenta iniciar sesión con la contraseña correcta pero su cuenta está bloqueada por fuerza bruta: el sistema debe rechazarlo igual, manteniendo el mismo mensaje genérico.
- Un usuario tiene una pestaña abierta sin interactuar: la sesión no debe prolongarse indefinidamente por el mero hecho de tener la pestaña abierta; la renovación depende de actividad real.

## Requirements *(mandatory)*

### Functional Requirements

**Registro**

- **FR-001**: El sistema DEBE permitir a cualquier visitante crear una cuenta proporcionando un email y una contraseña.
- **FR-002**: El sistema DEBE aceptar opcionalmente un nickname durante el registro, admitiendo letras minúsculas y mayúsculas.
- **FR-003**: Si el usuario no proporciona un nickname, el sistema DEBE asignarle automáticamente uno con el formato `user` seguido de un número aleatorio de 5 dígitos, garantizando que no colisione con un nickname existente.
- **FR-004**: El sistema DEBE rechazar un registro cuyo email ya esté en uso por otra cuenta.
- **FR-005**: El sistema DEBE rechazar un registro cuyo nickname ya esté en uso por otra cuenta.
- **FR-006**: El sistema DEBE almacenar las contraseñas de forma no reversible (hashing adecuado para contraseñas), nunca en claro.

**Login**

- **FR-007**: El sistema DEBE permitir a un usuario registrado iniciar sesión presentando su email y contraseña.
- **FR-008**: Ante cualquier credencial inválida (email no registrado, contraseña incorrecta o cuenta bloqueada temporalmente), el sistema DEBE devolver un único mensaje de error genérico que no permita distinguir entre los distintos motivos.

**Sesión y renovación**

- **FR-009**: Tras un login correcto, el sistema DEBE mantener al usuario autenticado entre visitas sin exigirle volver a introducir sus credenciales mientras la sesión siga siendo válida.
- **FR-010**: El sistema DEBE renovar automáticamente la sesión mientras el usuario esté realizando actividad autenticada, sin interrumpir su uso de la aplicación.
- **FR-011**: El sistema DEBE expirar la sesión tras un periodo razonable de inactividad y exigir un nuevo login para continuar.
- **FR-012**: Los tokens/credenciales de sesión NO DEBEN ser accesibles desde código ejecutado en el navegador (por ejemplo, mediante JavaScript del lado cliente).

**Logout**

- **FR-013**: El sistema DEBE ofrecer al usuario autenticado una acción explícita de cierre de sesión.
- **FR-014**: Tras el cierre de sesión, el sistema DEBE invalidar la sesión anterior, de forma que ninguna petición que reutilice sus credenciales pueda acceder a rutas protegidas.

**Protección de rutas**

- **FR-015**: El sistema DEBE considerar protegidas todas las rutas de la aplicación por defecto, con la excepción explícita de la ruta de inicio y la de registro.
- **FR-016**: El sistema DEBE impedir el acceso a rutas protegidas a usuarios no autenticados, redirigiéndolos a la pantalla de inicio de sesión.

**Protección contra fuerza bruta**

- **FR-017**: El sistema DEBE limitar el número de intentos de login fallidos consecutivos por cuenta en una ventana temporal, bloqueando temporalmente los siguientes intentos cuando se supere el umbral.
- **FR-018**: El sistema DEBE limitar también los intentos de login fallidos agregados por origen de la petición, para mitigar ataques distribuidos contra varias cuentas.
- **FR-019**: El bloqueo por fuerza bruta DEBE levantarse automáticamente al transcurrir la ventana temporal configurada sin nuevos intentos fallidos.

### Key Entities *(include if feature involves data)*

- **Usuario**: Persona con una cuenta en la aplicación. Atributos clave: identificador, email (único), nickname (único, asignado o auto-generado), credencial de acceso almacenada de forma no reversible, y metadatos para seguimiento de intentos fallidos (p. ej. número de fallos recientes, marca temporal de bloqueo).
- **Sesión**: Representa un inicio de sesión activo de un usuario. Atributos clave: referencia al usuario, momento de creación, momento de última actividad, momento de expiración, y estado (activa / invalidada por logout / expirada).
- **Registro de intentos de login**: Información que permite aplicar el límite de intentos. Atributos clave: cuenta objetivo y/o origen de la petición, marcas temporales de los intentos fallidos recientes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario nuevo puede completar el registro e iniciar sesión por primera vez en menos de 2 minutos, sin asistencia externa.
- **SC-002**: Tras un login correcto, el usuario puede cerrar el navegador y volver a abrir la aplicación dentro del periodo de validez de la sesión y acceder a su zona autenticada sin volver a introducir credenciales en el 100% de los casos.
- **SC-003**: Ante credenciales incorrectas, el 100% de las respuestas del sistema son indistinguibles entre sí en cuanto a mensaje, código de respuesta y tiempo de respuesta perceptible por el usuario; una persona externa no puede deducir si el email existe.
- **SC-004**: Cualquier intento de acceso a una ruta protegida sin una sesión válida es rechazado en el 100% de los casos, incluso cuando se reutiliza una sesión previamente cerrada por logout.
- **SC-005**: Un ataque automatizado que realice muchos intentos de login fallidos contra una misma cuenta es bloqueado antes de alcanzar un número de pruebas que suponga una amenaza realista sobre una contraseña razonable.
- **SC-006**: Cero tokens de sesión son accesibles desde scripts del lado cliente en pruebas de inspección (no aparecen en almacenamiento consultable por JavaScript).
- **SC-007**: Cero contraseñas se almacenan en texto plano: una inspección directa del almacenamiento de datos sólo muestra derivados no reversibles.

## Assumptions

- La aplicación es de tipo web con navegador como cliente principal. La protección "tokens no accesibles desde el navegador" se interpreta como que la credencial de sesión viaja en un canal no legible por código del lado cliente (por ejemplo, cookie con flags de seguridad adecuados), en lugar de quedar en almacenamiento cliente-lado.
- El formato concreto del email válido y las reglas mínimas de contraseña (longitud, complejidad) siguen los estándares habituales de aplicaciones web y se definirán en la fase de planificación; la spec exige "email válido" y "contraseña no trivial" sin fijar umbrales concretos.
- La verificación de email (doble opt-in) NO está en el alcance de esta versión: una cuenta queda utilizable inmediatamente tras el registro.
- La recuperación de contraseña ("olvidé mi contraseña") NO está en el alcance de esta versión; puede cubrirse en una spec posterior.
- La autenticación con proveedores externos (Google, GitHub, etc.) NO está en el alcance.
- Los umbrales concretos de bloqueo por fuerza bruta (número de intentos, ventana temporal, duración del bloqueo) se fijarán durante la planificación siguiendo prácticas habituales de la industria; lo que la spec exige es que exista el mecanismo y que sea efectivo.
- El periodo de validez de una sesión y la duración de la renovación automática son detalles de planificación; la spec exige únicamente que la sesión sobreviva a un cierre de navegador durante un tiempo razonable y que se renueve mientras el usuario esté activo.
- La sesión es por navegador/dispositivo; en esta versión no se exige gestionar explícitamente múltiples sesiones simultáneas del mismo usuario en dispositivos distintos (aunque tampoco se prohíbe).
