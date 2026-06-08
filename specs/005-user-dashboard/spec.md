# Feature Specification: Dashboard

**Feature Branch**: `005-user-dashboard`
**Created**: 2026-05-04
**Status**: Draft
**Input**: User description: "Dashboard global del usuario con saludo personalizado, tarjetas de estadísticas (torneos activos, victorias totales, mejor streak), sección 'Mis torneos' con torneos activos y próximos, y feed de actividad reciente del usuario y sus amigos."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Visión global al entrar: saludo y tarjetas de estadísticas (Priority: P1)

Tras autenticarse, el usuario aterriza en una página de inicio que lo saluda por su nickname e inmediatamente le muestra un conjunto de tarjetas con sus métricas clave (torneos activos, victorias totales, mejor streak), sin necesidad de navegar a otra sección para conocer su estado.

**Why this priority**: Es el contenido fundacional del dashboard: aunque los demás bloques (mis torneos, actividad) no estén disponibles, el usuario ya obtiene valor inmediato al ver de un vistazo su rendimiento personal. Sin este bloque, el dashboard no cumple su propósito de "visión global". Es independientemente desplegable: solo necesita los datos del propio usuario y el cómputo de sus métricas.

**Independent Test**: Autenticarse con un usuario que tenga historial de torneos y partidas, abrir la página de inicio y verificar que (a) aparece un saludo personalizado con su nickname, (b) un subtítulo fijo contextualiza la página, (c) se muestran las tarjetas de estadísticas con los valores reales calculados a partir de su historial y (d) los valores son consistentes con los datos del usuario en torneos y partidas.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado con nickname "playerOne", **When** accede a la página de inicio, **Then** el sistema muestra un saludo personalizado que incluye "playerOne" y un subtítulo fijo que contextualiza el contenido de la página.
2. **Given** un usuario que participa en 3 torneos en curso y participaba en 2 la semana anterior, **When** carga el dashboard, **Then** la tarjeta "Torneos activos" muestra el valor 3 y una variación positiva respecto a la semana anterior (+1).
3. **Given** un usuario con un historial de 12 victorias sobre 20 partidas jugadas, **When** carga el dashboard, **Then** la tarjeta "Victorias totales" muestra 12 victorias y un winrate del 60%.
4. **Given** un usuario cuya mejor racha histórica de victorias consecutivas fue de 5 partidas en el torneo "Spring Cup", **When** carga el dashboard, **Then** la tarjeta "Mejor streak" muestra el valor 5 y referencia al torneo "Spring Cup" donde se consiguió.
5. **Given** un usuario sin historial (recién registrado, sin torneos ni partidas), **When** carga el dashboard, **Then** las tarjetas se muestran con valores neutros (0, sin variación, sin torneo asociado) y no producen errores.

---

### User Story 2 - Mis torneos en curso y próximos en un vistazo (Priority: P2)

El usuario ve, sin abandonar el dashboard, una lista de tarjetas con sus torneos activos y próximos. Cada tarjeta resume lo esencial (nombre, estado, formato, número de jugadores y estado de la ronda actual o fecha de inicio) y un enlace "Ver todos" lleva a la sección completa de Torneos.

**Why this priority**: Convierte el dashboard de un panel solo de métricas en un panel accionable: el usuario puede saltar a sus torneos sin pasar por menús. Aporta valor por sí solo aunque el feed de actividad no esté disponible. Va después de P1 porque las estadísticas dan la "visión" que el dashboard promete antes que el detalle operativo.

**Independent Test**: Con un usuario que participe en al menos un torneo en curso y uno próximo, abrir el dashboard y verificar que (a) ambos torneos aparecen como tarjetas en la sección "Mis torneos", (b) cada tarjeta muestra los campos requeridos con valores correctos, (c) el estado mostrado coincide con el estado real del torneo, (d) torneos finalizados no aparecen, (e) torneos en los que el usuario no participa no aparecen, y (f) el enlace "Ver todos" navega a la sección de Torneos.

**Acceptance Scenarios**:

1. **Given** un usuario que participa en 2 torneos en curso y 1 próximo, **When** abre el dashboard, **Then** la sección "Mis torneos" muestra 3 tarjetas, cada una con nombre, estado ("En curso" o "Próximo"), formato, número de jugadores y, según el estado, la ronda actual o la fecha de inicio.
2. **Given** un torneo "Summer League" en curso en su ronda 3 con 16 jugadores y formato "Eliminación directa", en el que el usuario participa, **When** carga el dashboard, **Then** la tarjeta del torneo muestra esos datos exactos (nombre, estado "En curso", formato, 16 jugadores, ronda actual 3).
3. **Given** un torneo "Winter Cup" próximo, con fecha de inicio el 2026-06-15, en el que el usuario está inscrito, **When** carga el dashboard, **Then** la tarjeta del torneo muestra estado "Próximo" y la fecha de inicio (2026-06-15).
4. **Given** un torneo finalizado en el que el usuario participó, **When** el usuario abre el dashboard, **Then** el torneo NO aparece en la sección "Mis torneos".
5. **Given** un torneo en curso al que el usuario NO está inscrito, **When** carga el dashboard, **Then** ese torneo NO aparece en la sección "Mis torneos".
6. **Given** un usuario sin torneos activos ni próximos, **When** carga el dashboard, **Then** la sección "Mis torneos" muestra un estado vacío informativo, sin errores.
7. **Given** la sección "Mis torneos" visible, **When** el usuario pulsa el enlace "Ver todos", **Then** el sistema navega a la sección completa de Torneos.

---

### User Story 3 - Feed de actividad reciente del usuario y sus amigos (Priority: P3)

El usuario ve un feed cronológico (más reciente arriba) con eventos suyos y de sus amigos: victorias en partida, uniones a torneo, invitaciones a torneo y creaciones de torneo. Cada entrada indica quién hizo qué, en qué torneo y cuánto tiempo hace; los nombres de torneo y de usuario son clicables y llevan a la página correspondiente.

**Why this priority**: Es el bloque de mayor valor social y de "engagement", pero también el más complejo (depende de las relaciones de amistad de la feature 004 y de eventos de varias features previas). Se prioriza después porque el dashboard ya es útil sin él, y porque su ausencia no rompe los otros bloques.

**Independent Test**: Con un usuario A que tenga al menos un amigo B, generar eventos de los cuatro tipos (una victoria de A o de B, una unión de B a un torneo, una invitación enviada/recibida que involucre a A o B, una creación de torneo por A o B) y verificar que (a) todos aparecen en el feed del dashboard de A, (b) están ordenados de más reciente a más antiguo, (c) cada entrada indica actor, acción, torneo vinculado y tiempo transcurrido, (d) el actor y el torneo son enlaces que navegan a su página correspondiente y (e) NO aparecen eventos de usuarios que no son amigos de A.

**Acceptance Scenarios**:

1. **Given** un usuario A con amigos B y C, y un usuario D que NO es amigo de A, **When** B gana una partida, C se une a un torneo y D crea un torneo, **Then** el feed del dashboard de A muestra los eventos de B y C pero NO el de D.
2. **Given** un evento "B ganó una partida en el torneo Spring Cup", **When** A abre el dashboard, **Then** la entrada del feed muestra a B como actor, la acción "victoria en partida", el torneo "Spring Cup" vinculado y el tiempo transcurrido (p. ej. "hace 5 minutos").
3. **Given** una entrada del feed que menciona al usuario B y al torneo "Spring Cup", **When** A pulsa sobre el nombre de B, **Then** el sistema navega al perfil de B; **When** A pulsa sobre "Spring Cup", **Then** el sistema navega a la página del torneo.
4. **Given** varios eventos generados en distintos momentos, **When** A abre el dashboard, **Then** las entradas del feed aparecen ordenadas cronológicamente del más reciente al más antiguo.
5. **Given** un usuario A sin amigos y sin actividad propia reciente, **When** abre el dashboard, **Then** el feed muestra un estado vacío informativo, sin errores.
6. **Given** un evento de A "creé el torneo Winter Cup", **When** A abre el dashboard, **Then** su propia acción aparece también en el feed (la actividad propia del usuario es visible para él).
7. **Given** un evento del feed cuyo torneo o usuario referenciado ya no existe (cuenta eliminada o torneo borrado), **When** A abre el dashboard, **Then** el sistema renderiza la entrada de forma resiliente sin romper la página (p. ej., enlace inactivo o entrada omitida).

---

### Edge Cases

- **Usuario sin nickname todavía**: aunque el flujo normal de 001 garantiza nickname al registrar, si por alguna razón no hubiera, el saludo MUST tener un valor por defecto razonable y no romper la página.
- **Usuario sin historial alguno (recién registrado)**: tarjetas con valores neutros (0, sin variación, sin torneo asociado), "Mis torneos" y feed con estados vacíos informativos. Cero errores.
- **Variación semanal sin datos previos**: si el usuario no tenía métricas la semana anterior (p. ej., recién registrado), la tarjeta "Torneos activos" muestra el valor actual sin variación o con un indicador neutro, no un porcentaje sin sentido.
- **Mejor streak no asociable a un torneo concreto**: si la racha histórica abarca partidas de varios torneos, el sistema indica el torneo donde se obtuvo la última victoria de esa racha (regla determinista) o el que mayor número de victorias aportó; ver Asunciones.
- **Torneos cuyo estado cambia mientras el usuario está en el dashboard**: las métricas y bloques NO se actualizan en tiempo real (regla del prompt); el usuario verá el cambio en la próxima carga de la página.
- **Amigo que elimina su cuenta**: la actividad histórica de ese amigo deja de mostrarse en el feed (consistente con la pérdida de amistad establecida en 004).
- **Torneo eliminado**: las entradas del feed que lo mencionaban deben renderizarse sin romper la página; la práctica recomendada es ocultar la entrada o mostrar el nombre sin enlace.
- **Volumen alto de actividad reciente**: el feed se limita a un número razonable de entradas más recientes (sin paginación ni scroll infinito en esta versión, según prompt).
- **Conteo de jugadores en un torneo "Próximo"**: refleja el número de inscritos al momento de la carga; puede ser menor que el aforo total y no se actualiza en tiempo real.

## Requirements *(mandatory)*

### Functional Requirements

**Saludo y contexto de la página**

- **FR-001**: El sistema MUST mostrar al usuario autenticado un saludo personalizado que incluya su nickname al cargar el dashboard.
- **FR-002**: El sistema MUST mostrar un subtítulo fijo, idéntico para todos los usuarios, que contextualice el contenido de la página.

**Tarjetas de estadísticas**

- **FR-003**: El sistema MUST mostrar una tarjeta "Torneos activos" con el número de torneos en curso en los que el usuario participa actualmente.
- **FR-004**: La tarjeta "Torneos activos" MUST mostrar la variación de ese número respecto a la semana anterior (cuántos torneos activos tenía el usuario hace 7 días).
- **FR-005**: El sistema MUST mostrar una tarjeta "Victorias totales" con el número total de partidas ganadas por el usuario y el porcentaje de winrate (victorias / partidas jugadas).
- **FR-006**: El sistema MUST mostrar una tarjeta "Mejor streak" con la mejor racha histórica de victorias consecutivas del usuario y referencia al torneo en el que se consiguió.
- **FR-007**: Todas las métricas de las tarjetas MUST calcularse en el momento de la carga de la página y MUST NOT actualizarse en tiempo real durante la sesión del usuario.
- **FR-008**: Las tarjetas MUST manejar correctamente el caso de "sin datos" (usuario nuevo o sin historial), mostrando valores neutros sin errores ni divisiones por cero.

**Sección "Mis torneos"**

- **FR-009**: El sistema MUST mostrar una sección "Mis torneos" con los torneos activos y próximos en los que el usuario autenticado participa, en formato de tarjetas.
- **FR-010**: La sección "Mis torneos" MUST excluir torneos finalizados y MUST excluir torneos en los que el usuario no participa.
- **FR-011**: Cada tarjeta de torneo MUST mostrar: nombre del torneo, estado ("En curso" o "Próximo"), formato del torneo y número de jugadores.
- **FR-012**: Si el torneo está "En curso", la tarjeta MUST mostrar la información de la ronda actual; si está "Próximo", la tarjeta MUST mostrar la fecha de inicio.
- **FR-013**: La sección "Mis torneos" MUST incluir un enlace "Ver todos" que, al pulsarlo, MUST navegar a la sección completa de Torneos.
- **FR-014**: Si el usuario no tiene torneos activos ni próximos, la sección MUST mostrar un estado vacío informativo, sin errores.

**Feed de actividad reciente**

- **FR-015**: El sistema MUST mostrar un feed cronológico de actividad reciente con eventos del propio usuario y de sus amigos (relación de amistad establecida según la feature 004).
- **FR-016**: El feed MUST incluir al menos los siguientes tipos de evento: victoria en partida, unión a torneo, invitación a torneo y creación de torneo.
- **FR-017**: Cada entrada del feed MUST mostrar: el actor (usuario que originó el evento), la acción realizada, el torneo vinculado y el tiempo transcurrido desde el evento.
- **FR-018**: Los nombres de torneo y de usuario que aparecen en una entrada MUST ser clicables y MUST navegar a la página del torneo o al perfil del usuario, respectivamente.
- **FR-019**: El feed MUST excluir eventos cuyo actor NO sea ni el propio usuario ni un amigo del usuario.
- **FR-020**: El feed MUST estar ordenado cronológicamente del evento más reciente al más antiguo.
- **FR-021**: Si el usuario no tiene amigos ni actividad propia reciente, el feed MUST mostrar un estado vacío informativo, sin errores.
- **FR-022**: El feed MUST renderizar entradas de forma resiliente cuando el torneo o el usuario referenciado ya no exista, sin romper la página.

**Reglas transversales**

- **FR-023**: Todo acceso al dashboard y a sus datos MUST requerir autenticación válida; las peticiones realizadas en nombre de otro usuario MUST ser rechazadas.
- **FR-024**: El dashboard MUST estar disponible como página principal post-login (la página a la que el usuario llega tras autenticarse), sin requerir clics adicionales para acceder a él.
- **FR-025**: El sistema MUST ofrecer [NEEDS CLARIFICATION: el prompt indica "4 tarjetas" pero solo describe 3 (Torneos activos, Victorias totales, Mejor streak); ¿cuál es la 4ª tarjeta y qué métrica representa? Candidatos razonables: número de amigos, invitaciones pendientes, torneos creados por el usuario, partidas jugadas totales].

### Key Entities *(include if feature involves data)*

- **Usuario (existente)**: definido en 001-user-auth, enriquecido en 003-edit-profile (foto, juegos vinculados) y en 004-add-friends (relaciones de amistad). El dashboard usa el nickname para el saludo y el conjunto de amistades para filtrar el feed de actividad.
- **Torneo (existente)**: definido en 002-tournament-management. El dashboard lee nombre, estado, formato, número de jugadores, ronda actual y fecha de inicio para alimentar las tarjetas de "Mis torneos" y como referencia en las tarjetas de estadísticas y el feed.
- **Participación en torneo (existente)**: relación entre usuario y torneo definida en 002. El dashboard la usa para determinar "torneos activos" del usuario y filtrar "Mis torneos".
- **Partida / resultado de partida (existente)**: definido en 002 (entidad `matches`). El dashboard la usa para calcular victorias totales, winrate y la mejor racha de victorias consecutivas.
- **Invitación a torneo (existente)**: definida en 002. Aparece como tipo de evento en el feed.
- **Amistad (existente)**: definida en 004. Determina qué usuarios distintos del propio aportan eventos al feed.
- **Evento de actividad (concepto del dashboard)**: representación lógica de un suceso reciente (victoria en partida, unión a torneo, invitación a torneo, creación de torneo). No es necesariamente una nueva tabla; puede derivarse de los registros existentes (matches, participants, invitations, tournaments) leídos y unificados al cargar el dashboard. Atributos lógicos: actor (usuario), tipo de evento, torneo asociado, marca de tiempo del evento.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Al acceder a la página de inicio post-login, el dashboard se muestra completo (saludo, tarjetas, mis torneos y feed) en menos de 2 segundos en condiciones normales.
- **SC-002**: En el 100% de las cargas, el saludo incluye el nickname real del usuario autenticado y el subtítulo aparece sin variar.
- **SC-003**: En el 100% de las cargas, las tarjetas de estadísticas muestran valores derivados del historial real del usuario; un usuario sin historial obtiene valores neutros (0, sin porcentaje no definido, sin torneo asociado) sin errores visibles.
- **SC-004**: En el 100% de las cargas, la sección "Mis torneos" lista únicamente torneos en los que el usuario participa y que están en curso o próximos; ningún torneo finalizado ni torneo ajeno aparece.
- **SC-005**: En el 100% de las cargas, el feed contiene únicamente eventos del propio usuario y de sus amigos; ningún evento de usuarios no-amigos aparece.
- **SC-006**: En el 100% de las cargas, las entradas del feed están ordenadas de más reciente a más antiguo y muestran actor, acción, torneo y tiempo transcurrido.
- **SC-007**: En el 100% de las entradas del feed que mencionan a un usuario o torneo existente, el enlace navega correctamente a su página.
- **SC-008**: Un usuario nuevo, sin torneos, partidas ni amigos, puede abrir el dashboard sin obtener errores y ve estados vacíos informativos en cada sección.
- **SC-009**: El enlace "Ver todos" de la sección "Mis torneos" navega a la sección completa de Torneos en el 100% de los casos.
- **SC-010**: Las métricas mostradas no cambian durante la sesión del usuario sin recargar la página: el contenido del dashboard refleja el estado al momento de la última carga.

## Assumptions

- El "subtítulo fijo" es un texto único y constante (p. ej., una frase que sintetiza el propósito del dashboard) definido por el equipo de producto; esta feature solo garantiza su presencia, no su redacción exacta.
- "Torneo activo" se interpreta como un torneo en estado "En curso" según los estados ya definidos en la feature 002.
- "Variación respecto a la semana anterior" se calcula comparando el número de torneos activos del usuario en el momento actual con el número de torneos activos hace exactamente 7 días (mismo cálculo en el momento de carga).
- "Mejor streak" se calcula sobre el historial completo de partidas ganadas/perdidas del usuario en torneos. Cuando la racha abarca varios torneos, se asocia al torneo donde se obtuvo la **última** victoria de esa racha (regla determinista y trazable).
- El feed de actividad se limita a un número razonable de entradas más recientes (por ejemplo, decenas) para esta versión; el límite exacto se decide en planificación. No hay paginación ni scroll infinito en esta versión.
- El "tiempo transcurrido" se muestra de forma relativa cuando es reciente ("hace X minutos/horas") y puede mostrar fecha absoluta cuando supere cierto umbral (p. ej., varios días); el detalle exacto se decide en planificación.
- La actividad propia del usuario es visible en su propio feed (el dashboard también es una "vista global" de lo que ha hecho recientemente, no solo de los amigos).
- Los eventos del feed se derivan de los registros existentes (`matches`, `participants`, `invitations`, `tournaments`) sin necesidad de una tabla de actividad nueva; la planificación técnica decide la estrategia de consulta.
- La autenticación, el manejo de sesiones y la protección de los endpoints reutilizan los mecanismos definidos en 001-user-auth; esta feature no redefine reglas de seguridad.
- La relación de amistad (que determina qué eventos ajenos aparecen en el feed) se basa en las amistades simétricas definidas en 004-add-friends; esta feature no introduce lógica adicional de "seguir" o "bloquear".
- El dashboard es la página de aterrizaje post-login del producto; la navegación al resto de secciones (Torneos, Perfil, Amigos) se realiza desde el menú principal de la app, fuera del alcance de esta feature.
- El soporte específico para móvil queda fuera del alcance explícito de esta feature; se diseña pensando en un cliente web autenticado.
