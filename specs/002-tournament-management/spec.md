# Feature Specification: Creación y gestión de torneos con calendario automático

**Feature Branch**: `002-tournament-management`
**Created**: 2026-04-24
**Status**: Draft
**Input**: User description: "Creación y gestión de torneos de League of Legends con calendario automático, vinculación de cuenta Riot, invitación de amigos, generación de códigos de sala, verificación de resultados por API, override manual, clasificación en tiempo real y avance automático."

> ⚠️ **Nota de implementación:** La **vinculación de cuenta de juego** (Riot / League of Legends) es una dependencia transversal de esta feature. Está **fuera del alcance de la iteración actual** y se implementará en una fase posterior. Los requisitos y escenarios que dependen de ella quedan marcados con el símbolo ⚠️ y se consideran **bloqueados** hasta que dicha funcionalidad esté disponible.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Organizar un torneo de extremo a extremo (Priority: P1)

Un usuario registrado ~~vinculado de su cuenta de uno de los juegos permitidos de la app (ahora solo está League of Legends)~~ ⚠️ **[vinculación de cuenta de juego — no implementado]**, crea un torneo indicando nombre, fecha orientativa y formato (round-robin o eliminación directa), invita a amigos ~~que también tienen cuenta de juego vinculada~~ ⚠️ **[requisito de cuenta vinculada en invitados — no implementado]**, abre inscripciones, recibe confirmaciones y, con al menos dos participantes, inicia el torneo. En ese momento el sistema genera automáticamente el calendario (todas las rondas en round-robin o la primera ronda en eliminación directa) y un código de sala único por cada enfrentamiento, visible para los dos jugadores y el organizador.

**Why this priority**: Es el núcleo del producto. Sin este flujo no existe torneo. Todas las demás historias amplían o complementan la experiencia que se desbloquea aquí.

**Independent Test**: Puede validarse extremo a extremo en una sesión: un usuario ~~vincula su cuenta~~ ⚠️ **[vinculación de cuenta — no implementado]**, crea un torneo, invita a 3 amigos ~~con cuenta vinculada~~ ⚠️ **[requisito de cuenta vinculada — no implementado]**, los amigos aceptan, el organizador abre inscripciones e inicia el torneo; se comprueba que existe un calendario coherente y un código de sala único por enfrentamiento de la primera ronda. Entrega valor por sí mismo aunque aún no haya verificación de resultados.

**Acceptance Scenarios**:

1. **Given** un usuario con ~~cuenta de juego vinculada~~ ⚠️ **[cuenta vinculada — no implementado]**, **When** crea un torneo con nombre, fecha y formato round-robin, **Then** el torneo queda creado en estado "Borrador" y el creador queda asignado como organizador.
2. **Given** un torneo en "Borrador", **When** el organizador abre inscripciones, **Then** el torneo transita a "Inscripción abierta" sin iniciar el torneo.
3. **Given** un torneo en "Inscripción abierta" con un amigo invitado que ~~tiene cuenta de ese juego vinculada~~ ⚠️ **[cuenta vinculada en invitado — no implementado]**, **When** el amigo acepta la invitación dentro de 48 horas, **Then** queda registrado como participante confirmado y se le notifica in-app.
4. **Given** un torneo con al menos 2 participantes confirmados, **When** el organizador pulsa "Iniciar torneo", **Then** el torneo transita a "En curso", se bloquean formato/participantes/configuración y se generan los enfrentamientos necesarios y sus códigos de sala.
5. **Given** un torneo round-robin iniciado con N participantes, **When** se consulta el calendario, **Then** cada participante tiene exactamente un enfrentamiento contra cada otro participante; si N es impar, cada ronda incluye un bye rotativo sin repetir descanso mientras queden jugadores que no hayan descansado.
6. **Given** un torneo de eliminación directa iniciado con un número de participantes que no es potencia de 2, **When** se consulta la primera ronda, **Then** el cuadro está equilibrado mediante byes automáticos.

---

### User Story 2 - Verificar resultados de partida por la API de Riot (Priority: P2)

> ⚠️ **Esta historia depende de la vinculación de cuenta de juego y de la integración con la API de Riot, ambas fuera del alcance de la iteración actual. Queda bloqueada hasta que dichas funcionalidades estén disponibles.**

Tras disputarse un enfrentamiento, cualquiera de los dos jugadores o el organizador puede solicitar la verificación del resultado. El sistema busca la partida asociada al código de sala en la API de Riot, comprueba que cumple todas las condiciones requeridas (ambos jugadores presentes, equipos opuestos, inicio posterior a la creación del código, duración ≥ 5 minutos, modo CLASSIC) y, si todo es correcto, registra el resultado, marca el enfrentamiento como "Verificado por API" y, en eliminación directa, avanza al ganador automáticamente.

**Why this priority**: Es el diferenciador funcional del producto frente a una hoja de cálculo manual. Reduce drásticamente la carga operativa del organizador y las disputas. No es crítico para el MVP absoluto (un torneo puede completarse solo con override manual), pero sin esto el valor del producto baja mucho.

**Independent Test**: Con un torneo iniciado y un enfrentamiento con código de sala generado, pueden simularse partidas (reales o con fixtures de la API) y verificarse que el resultado se registra correctamente como "Verificado por API" y, en eliminación directa, que el ganador avanza a la ronda siguiente. Entrega valor sin depender de la historia de override manual.

**Acceptance Scenarios**:

1. **Given** un enfrentamiento con código de sala generado y una partida jugada en Riot que cumple todas las validaciones ⚠️ **[integración API Riot — no implementado]**, **When** un jugador pulsa "Verificar resultado", **Then** el enfrentamiento queda marcado como "Verificado por API" con ganador registrado.
2. **Given** un enfrentamiento en eliminación directa verificado por API ⚠️ **[no implementado]**, **When** la verificación se completa, **Then** el ganador avanza automáticamente a la ronda siguiente; si es el último enfrentamiento de la ronda, el sistema genera los enfrentamientos de la siguiente ronda y sus códigos de sala.
3. **Given** una partida encontrada en el historial pero con duración inferior a 5 minutos ⚠️ **[integración API Riot — no implementado]**, **When** se intenta verificar, **Then** el sistema rechaza la verificación y el enfrentamiento permanece pendiente.
4. **Given** una partida encontrada con los dos jugadores en el mismo equipo ⚠️ **[integración API Riot — no implementado]**, **When** se intenta verificar, **Then** el sistema rechaza la verificación.
5. **Given** que la única partida encontrada entre ambos jugadores tiene timestamp anterior a la creación del código de sala ⚠️ **[integración API Riot — no implementado]**, **When** se intenta verificar, **Then** el sistema rechaza la verificación.
6. **Given** que la partida encontrada no es de modo CLASSIC ⚠️ **[integración API Riot — no implementado]**, **When** se intenta verificar, **Then** el sistema rechaza la verificación.

---

### User Story 3 - Registrar resultado manualmente con etiqueta permanente (Priority: P2)

Cuando la API no puede verificar una partida (fallo de datos, servicio no disponible, partida jugada fuera del sistema) ⚠️ **[integración API Riot — no implementado; en la iteración actual este será el único método de registro de resultados]** o el organizador decide intervenir por cualquier motivo, el organizador puede registrar el resultado indicando el ganador. El enfrentamiento queda marcado de forma permanente como "Introducido manualmente" y esa etiqueta no se pierde aunque posteriormente la partida pudiera verificarse por API.

**Why this priority**: Es la vía de escape que mantiene la continuidad del torneo ante cualquier incidencia técnica. Sin este mecanismo, un fallo en la API bloquea el torneo. Por eso es P2 (al mismo nivel que la verificación automática), no P3.

**Independent Test**: Puede probarse directamente sobre cualquier enfrentamiento pendiente (con o sin código de sala generado): el organizador registra un ganador, el enfrentamiento queda "Introducido manualmente" con etiqueta permanente, y —en eliminación directa— el ganador avanza.

**Acceptance Scenarios**:

1. **Given** un enfrentamiento pendiente donde la verificación por API ha fallado ⚠️ **[integración API Riot — no implementado]** (o directamente desde cualquier enfrentamiento pendiente en la iteración actual), **When** el organizador registra manualmente al jugador ganador, **Then** el enfrentamiento queda marcado como "Introducido manualmente" y el ganador avanza (en eliminación directa).
2. **Given** un enfrentamiento marcado como "Introducido manualmente", **When** se intenta ocultar o cambiar esa etiqueta, **Then** el sistema no lo permite; la etiqueta es permanente.
3. **Given** un enfrentamiento marcado como "Introducido manualmente", **When** posteriormente la partida sí cumple todas las validaciones de API ⚠️ **[integración API Riot — no implementado]**, **Then** el enfrentamiento sigue marcado como "Introducido manualmente" (no se reetiqueta como "Verificado por API").
4. **Given** un enfrentamiento marcado como "Introducido manualmente", **When** un jugador intenta disputar el resultado, **Then** el sistema no permite abrir la disputa.

---

### User Story 4 - Seguir la clasificación y el cuadro en tiempo real (Priority: P2)

Cualquier participante puede consultar en cualquier momento la tabla de clasificación (round-robin) o el cuadro de eliminación, con los resultados confirmados hasta el momento, los estados de los enfrentamientos (pendiente, verificado por API ⚠️ **[no implementado]**, introducido manualmente), sus próximos enfrentamientos con el código de sala y los resultados anteriores. En round-robin la tabla se reordena automáticamente tras cada resultado confirmado aplicando los criterios de desempate definidos.

**Why this priority**: Es parte esencial de la experiencia durante el torneo, pero no bloquea la disputa (un torneo puede completarse sin vista de clasificación si los resultados se almacenan). Por eso queda en P2, subordinada a la disputa real.

**Independent Test**: Con un torneo en curso y varios resultados confirmados (de API ⚠️ **[no implementado]** o manuales), puede verificarse que la tabla/cuadro refleja los resultados, aplica bien los desempates en round-robin, distingue estados y muestra correctamente el siguiente enfrentamiento y su código de sala para cada participante.

**Acceptance Scenarios**:

1. **Given** un torneo round-robin con varios resultados confirmados, **When** un participante consulta la clasificación, **Then** ve la tabla ordenada por (1) victorias, (2) resultado del enfrentamiento directo entre empatados, (3) fecha de inscripción al torneo en caso de empate circular.
2. **Given** un torneo round-robin donde un participante tuvo un bye en una ronda, **When** se calcula la clasificación, **Then** el bye no suma puntos.
3. **Given** un torneo de eliminación directa en curso, **When** un participante consulta el cuadro, **Then** ve los enfrentamientos pasados con su resultado y estado, y los enfrentamientos pendientes.
4. **Given** un enfrentamiento confirmado por cualquier vía, **When** se consulta la clasificación o el cuadro, **Then** se muestra explícitamente si fue "Verificado por API" ⚠️ **[no implementado]** o "Introducido manualmente", sin ambigüedad.
5. **Given** un participante con un enfrentamiento pendiente, **When** consulta sus próximos enfrentamientos, **Then** ve el código de sala asociado y el estado "pendiente".

---

### User Story 5 - Modificar el torneo antes de iniciarlo (Priority: P3)

Mientras el torneo está en "Borrador" o "Inscripción abierta", el organizador puede cambiar el nombre, la fecha orientativa, el formato (round-robin ↔ eliminación directa), invitar a más amigos, eliminar participantes confirmados o cancelar invitaciones pendientes. Al iniciar el torneo, todos estos parámetros quedan bloqueados.

**Why this priority**: Mejora la flexibilidad del organizador antes del inicio, pero el flujo mínimo puede existir sin ella (creando el torneo correctamente a la primera).

**Independent Test**: Partiendo de un torneo en "Borrador" puede modificarse cada parámetro listado, y partiendo de un torneo en "En curso" debe comprobarse que ninguno de ellos es editable.

**Acceptance Scenarios**:

1. **Given** un torneo en "Borrador", **When** el organizador cambia el formato de round-robin a eliminación directa, **Then** el cambio se acepta.
2. **Given** un torneo en "Inscripción abierta" con un participante confirmado, **When** el organizador elimina al participante, **Then** el participante queda fuera del torneo.
3. **Given** un torneo en "En curso", **When** el organizador intenta cambiar el formato o el nombre, **Then** el sistema lo rechaza.
4. **Given** una invitación pendiente sin responder, **When** el organizador la cancela antes de 48 horas, **Then** la invitación queda anulada y el invitado no puede aceptarla.

---

### User Story 6 - Cancelar un torneo (Priority: P3)

El organizador puede cancelar el torneo desde cualquier estado no terminal. Todos los participantes reciben notificación in-app. El torneo cancelado queda en estado terminal y visible en solo lectura para los participantes.

**Why this priority**: Es una capacidad administrativa necesaria pero infrecuente respecto al flujo principal.

**Independent Test**: Puede validarse desde cada estado no terminal (Borrador, Inscripción abierta, En curso): el organizador cancela, los participantes reciben notificación, el estado pasa a "Cancelado" y ya no admite cambios.

**Acceptance Scenarios**:

1. **Given** un torneo en "En curso", **When** el organizador lo cancela, **Then** el torneo pasa a "Cancelado", todos los participantes reciben una notificación in-app y el torneo queda en solo lectura.
2. **Given** un torneo en "Finalizado", **When** el organizador intenta cancelarlo, **Then** el sistema lo rechaza (estado terminal).
3. **Given** un torneo "Cancelado", **When** un participante lo consulta, **Then** puede ver los datos históricos pero no realizar ninguna acción sobre él.

---

### Edge Cases

- Una invitación expira por el paso de 48 horas mientras el invitado está con la pantalla abierta; al intentar aceptar, el sistema debe rechazar la acción y comunicar la expiración.
- Un usuario desvincula su cuenta de LoL ⚠️ **[desvinculación de cuenta — no implementado]** teniendo invitaciones pendientes (aún no es participante confirmado); esas invitaciones dejan de poder aceptarse porque ya no cumple el prerrequisito de cuenta vinculada y validada ⚠️ **[prerrequisito de cuenta vinculada — no implementado]**.
- Round-robin con 3 o más participantes cuyos resultados directos forman un ciclo (empate circular): el desempate se resuelve por fecha de inscripción.
- Eliminación directa con número de participantes no potencia de 2 (p. ej. 6): la primera ronda incluye los byes necesarios para que la segunda ronda sí sea potencia de 2.
- Se ha generado el código de sala pero los jugadores disputan la partida en otra sala (sin el código asignado): la verificación por API ⚠️ **[no implementado]** no la encontrará asociada al código; solo queda la vía de override manual.
- La API de Riot está temporalmente no disponible ⚠️ **[integración API Riot — no implementado]**: la verificación falla con un mensaje comprensible y el enfrentamiento permanece pendiente; el organizador puede usar override manual si lo considera.
- El organizador elimina a un participante confirmado después de iniciar el torneo: el sistema lo impide (participantes bloqueados al iniciar).
- El último resultado pendiente de un torneo se confirma: el torneo transita automáticamente a "Finalizado" sin acción del organizador.
- Un usuario participa en varios torneos activos al mismo tiempo: la restricción de desvinculación ⚠️ **[desvinculación de cuenta — no implementado]** se aplica si está participando en al menos un torneo activo.
- Dos participantes tienen fecha de inscripción idéntica (mismo segundo) en un empate circular: se aplica un desempate adicional estable (criterio interno, p. ej. identificador del participante) documentado en Assumptions.

---

## Requirements *(mandatory)*

### Functional Requirements

#### Creación de torneo

- **FR-005**: El sistema MUST permitir a cualquier usuario registrado crear un torneo indicando nombre, fecha y hora de inicio orientativa, y formato (round-robin o eliminación directa).
- **FR-006**: El sistema MUST asignar automáticamente al creador como organizador.
- **FR-007**: El sistema MUST crear el torneo en estado "Borrador".
- **FR-008**: El sistema MUST tratar la fecha y hora de inicio como orientativa; no MUST bloquear el inicio del torneo basándose en ella.

#### Invitación y confirmación de participantes

- **FR-009**: El sistema MUST permitir al organizador invitar a usuarios añadidos como amigos en la aplicación (incluyéndose a sí mismo).
- **FR-010**: ⚠️ **[No implementado]** El sistema MUST restringir las invitaciones a usuarios con una cuenta de LoL vinculada y validada. *(Bloqueado hasta que la vinculación de cuenta de juego esté disponible. En la iteración actual, cualquier usuario registrado puede ser invitado sin este requisito.)*
- **FR-011**: El sistema MUST enviar una notificación in-app al usuario invitado.
- **FR-012**: El sistema MUST permitir al invitado aceptar o rechazar la invitación.
- **FR-013**: El sistema MUST expirar automáticamente las invitaciones pendientes al cumplirse 48 horas desde su envío.
- **FR-014**: El sistema MUST permitir al organizador cancelar una invitación pendiente antes de que expire.
- **FR-015**: El sistema MUST permitir al organizador eliminar a un participante ya confirmado mientras el torneo esté en "Borrador" o "Inscripción abierta".

#### Transiciones de estado y bloqueo

- **FR-016**: El sistema MUST soportar los estados de torneo: "Borrador", "Inscripción abierta", "En curso", "Finalizado", "Cancelado".
- **FR-017**: El sistema MUST permitir al organizador transitar de "Borrador" a "Inscripción abierta" mediante acción explícita, sin iniciar el torneo.
- **FR-018**: El sistema MUST permitir iniciar el torneo (transitar a "En curso") únicamente si hay al menos 2 participantes confirmados.
- **FR-019**: Al iniciar el torneo, el sistema MUST bloquear formato, participantes y configuración general contra modificaciones.
- **FR-020**: El sistema MUST transitar el torneo a "Finalizado" automáticamente al confirmarse el último resultado pendiente, sin requerir acción del organizador.

#### Modificaciones antes de iniciar

- **FR-021**: Mientras el torneo esté en "Borrador" o "Inscripción abierta", el sistema MUST permitir al organizador cambiar el nombre, la fecha/hora de inicio, el formato (round-robin ↔ eliminación directa), invitar a más amigos, eliminar participantes confirmados y cancelar invitaciones pendientes.
- **FR-022**: Una vez iniciado el torneo, el sistema MUST rechazar cualquier modificación de los parámetros listados en FR-021.

#### Generación de calendario

- **FR-023**: Al iniciar un torneo round-robin, el sistema MUST generar todos los enfrentamientos garantizando que cada participante se enfrenta exactamente una vez a cada otro participante.
- **FR-024**: Si el número de participantes en round-robin es impar, el sistema MUST asignar un bye rotativo por ronda de modo que ningún jugador descanse dos veces mientras queden jugadores que aún no hayan descansado.
- **FR-025**: Al iniciar un torneo de eliminación directa, el sistema MUST generar el cuadro de la primera ronda.
- **FR-026**: Si el número de participantes en eliminación directa no es potencia de 2, el sistema MUST asignar byes automáticos en la primera ronda para equilibrar el cuadro.
- **FR-027**: En eliminación directa, el sistema MUST NO generar los enfrentamientos de rondas posteriores hasta que todos los resultados de la ronda anterior estén confirmados.
- **FR-028**: Al confirmarse el último resultado de una ronda en eliminación directa, el sistema MUST generar automáticamente los enfrentamientos de la siguiente ronda y sus códigos de sala.
- **FR-029**: El sistema MUST NO regenerar el calendario una vez que el torneo ha iniciado.
- **FR-030**: El sistema MUST tratar round-robin y eliminación directa como mutuamente excluyentes (sin comportamiento híbrido).

#### Códigos de sala (Tournament Code)

- **FR-031**: Al generarse un enfrentamiento, el sistema MUST generar un código de sala único restringido exclusivamente a los dos jugadores de ese enfrentamiento.
- **FR-032**: El sistema MUST mostrar el código de sala de cada enfrentamiento a ambos jugadores y al organizador en el detalle del enfrentamiento.
- **FR-033**: El sistema MUST registrar el timestamp de creación del código para permitir la validación temporal (FR-036 ⚠️ **[no implementado]**).

#### Verificación de resultados por API

> ⚠️ **Todos los requisitos de esta sección (FR-034 a FR-039) están fuera del alcance de la iteración actual.** Dependen de la integración con la API de Riot y de la vinculación de cuenta de juego.

- **FR-034**: ⚠️ **[No implementado]** El sistema MUST permitir que cualquiera de los dos jugadores del enfrentamiento o el organizador dispare la verificación del resultado.
- **FR-035**: ⚠️ **[No implementado]** El sistema MUST consultar la API de Riot y rechazar la verificación si no encuentra una partida asociada al código de sala del enfrentamiento con ambos jugadores.
- **FR-036**: ⚠️ **[No implementado]** El sistema MUST validar, al verificar, que: (a) ambos jugadores del enfrentamiento están presentes, (b) los dos jugadores están en equipos opuestos (teamId distinto), (c) el timestamp de inicio de la partida es posterior a la creación del código de sala, (d) la duración de la partida es ≥ 5 minutos, (e) el modo de juego es CLASSIC.
- **FR-037**: ⚠️ **[No implementado]** Si todas las validaciones de FR-036 pasan, el sistema MUST registrar el resultado y marcar el enfrentamiento como "Verificado por API".
- **FR-038**: ⚠️ **[No implementado]** En eliminación directa, al marcarse un enfrentamiento como "Verificado por API", el sistema MUST avanzar al ganador a la siguiente ronda automáticamente.
- **FR-039**: ⚠️ **[No implementado]** El sistema MUST NO aceptar como válida una partida encontrada en el historial de los jugadores que no corresponda al código de sala asignado a ese enfrentamiento.

#### Override manual de resultados

- **FR-040**: El sistema MUST permitir al organizador registrar el resultado manualmente indicando el jugador ganador cuando la verificación por API falla ⚠️ **[integración API Riot — no implementado]** o el organizador decide intervenir. *(En la iteración actual, este será el único mecanismo de registro de resultados.)*
- **FR-041**: Un enfrentamiento registrado manualmente MUST quedar marcado como "Introducido manualmente".
- **FR-042**: La etiqueta "Introducido manualmente" MUST ser permanente e inamovible; aunque más tarde la partida cumpla las validaciones de API ⚠️ **[no implementado]**, el enfrentamiento MUST mantener esa etiqueta.
- **FR-043**: En eliminación directa, al marcarse un enfrentamiento como "Introducido manualmente", el sistema MUST avanzar al ganador a la siguiente ronda automáticamente.
- **FR-044**: El sistema MUST NO admitir disputas de los jugadores contra un resultado "Introducido manualmente".

#### Restricciones sobre resultados

- **FR-045**: El sistema MUST NO permitir registrar resultados en enfrentamientos de rondas que aún no han comenzado.
- **FR-046**: El sistema MUST NO avanzar al ganador de un enfrentamiento si su resultado no ha sido confirmado.

#### Clasificación round-robin

- **FR-047**: En round-robin, el sistema MUST mantener una tabla de clasificación actualizada tras cada resultado confirmado.
- **FR-048**: La clasificación MUST ordenarse por: (1) victorias (1 punto por victoria, 0 por derrota; los byes NO suman puntos), (2) resultado del enfrentamiento directo entre empatados, (3) si el enfrentamiento directo no resuelve el empate (empate circular), fecha de inscripción al torneo (se clasifica antes quien se inscribió antes).

#### Avance en eliminación directa y finalización

- **FR-049**: Al confirmarse el resultado de un enfrentamiento (por API ⚠️ **[no implementado]** o por override), el sistema MUST avanzar al ganador a la siguiente ronda.
- **FR-050**: Al confirmarse el resultado de la gran final en eliminación directa, el sistema MUST transitar el torneo a "Finalizado".

#### Consulta durante el torneo

- **FR-051**: El sistema MUST permitir a cualquier participante consultar sus próximos enfrentamientos, incluyendo el código de sala y el estado (pendiente, verificado por API ⚠️ **[no implementado]**, introducido manualmente).
- **FR-052**: El sistema MUST permitir a cualquier participante consultar sus resultados anteriores con el mismo detalle de estado.
- **FR-053**: El sistema MUST permitir a cualquier participante consultar la tabla de clasificación (round-robin) o el cuadro de eliminación (eliminación directa) con los resultados ya confirmados.
- **FR-054**: El sistema MUST mostrar explícitamente y sin ambigüedad si un resultado fue "Verificado por API" ⚠️ **[no implementado]** o "Introducido manualmente".

#### Cancelación

- **FR-055**: El sistema MUST permitir al organizador cancelar el torneo desde cualquier estado salvo "Finalizado".
- **FR-056**: Un torneo cancelado MUST ser un estado terminal; no admite más transiciones.
- **FR-057**: Al cancelar un torneo, el sistema MUST enviar una notificación in-app a todos los participantes.
- **FR-058**: El sistema MUST mantener un torneo cancelado visible en solo lectura para los participantes.

---

### Key Entities

- **Usuario**: Cuenta registrada en la aplicación (proviene de feature 001-user-auth). Puede tener como máximo una cuenta de LoL vinculada ⚠️ **[vinculación de cuenta — no implementado]** y una lista de amistades.
- **Cuenta de League of Legends vinculada**: ⚠️ **[No implementado]** Asociación entre un usuario y un Riot ID validado. Atributos clave: Riot ID (`NombreJugador#TAG`), estado de validación, fecha de vinculación. Un usuario tiene como mucho una. *(Esta entidad no existe en la iteración actual.)*
- **Amistad**: Relación bidireccional entre dos usuarios de la aplicación. Prerrequisito para poder invitar a un torneo (asunción; ver Assumptions).
- **Torneo**: Competición organizada por un usuario. Atributos: nombre, fecha de inicio orientativa, formato (round-robin | eliminación directa), estado (Borrador | Inscripción abierta | En curso | Finalizado | Cancelado), organizador, fecha de creación. Relacionado con: participantes, invitaciones, enfrentamientos, clasificación o cuadro.
- **Invitación a torneo**: Propuesta enviada a un usuario para participar. Atributos: torneo, usuario invitado, fecha de envío, fecha de expiración (48 horas), estado (pendiente | aceptada | rechazada | expirada | cancelada).
- **Participante**: Usuario confirmado en un torneo. Atributos: torneo, usuario, fecha de inscripción (timestamp de aceptación), indicadores derivados para desempates. *(En la iteración actual no se requiere cuenta de juego vinculada para ser participante.)*  ⚠️ **[requisito de cuenta vinculada — no implementado]**
- **Enfrentamiento**: Partida entre dos participantes en una ronda concreta del torneo. Atributos: torneo, ronda, jugador 1, jugador 2, código de sala, estado (pendiente | verificado por API ⚠️ **[no implementado]** | introducido manualmente), ganador (cuando resuelto), timestamp de resolución.
- **Código de sala (Tournament Code)**: Identificador único por enfrentamiento que restringe la partida a los dos jugadores del enfrentamiento. Atributos: enfrentamiento, timestamp de creación. *(Nota: la restricción técnica del código en la plataforma de Riot depende de la integración con la API de Riot ⚠️ **[no implementado]**; en la iteración actual el código se genera como identificador interno.)*
- **Ronda**: Agrupación de enfrentamientos con número de secuencia dentro de un torneo. Estado derivado: completada cuando todos sus enfrentamientos están resueltos.
- **Bye**: Asignación de descanso a un participante en una ronda concreta (para round-robin impar o primera ronda de eliminación directa desequilibrada). No puntúa en la clasificación.
- **Entrada de clasificación** (round-robin): Derivada. Atributos: torneo, participante, puntos, victorias, derrotas, byes. Se recalcula tras cada resultado confirmado.
- **Cuadro** (eliminación directa): Estructura de rondas con enfrentamientos; los de rondas posteriores a la primera se generan al cerrarse la anterior.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un organizador puede completar el flujo "~~vincular cuenta →~~ ⚠️ **[no implementado]** crear torneo → invitar 3 amigos → abrir inscripciones → iniciar torneo" en menos de 10 minutos la primera vez que lo usa.
- **SC-002**: ⚠️ **[No implementado]** En torneos donde todos los participantes disputan sus partidas usando el código de sala generado, al menos el 95 % de los enfrentamientos se confirman como "Verificado por API" sin necesidad de intervención manual del organizador. *(Bloqueado hasta que la integración con la API de Riot esté disponible.)*
- **SC-003**: Tras confirmarse un resultado, la clasificación (round-robin) o el cuadro (eliminación directa) reflejan el cambio en menos de 5 segundos para cualquier participante que consulte en ese momento.
- **SC-004**: El 100 % de los resultados marcados como "Introducido manualmente" mantienen esa etiqueta durante toda la vida del torneo, aun cuando la partida subyacente pudiera verificarse posteriormente por API ⚠️ **[no implementado]**.
- **SC-005**: En el 100 % de los torneos round-robin con al menos un bye, ningún bye suma puntos en la clasificación final.
- **SC-006**: En round-robin con N participantes impar, ningún jugador descansa dos veces mientras queden jugadores que no hayan descansado ni una vez (propiedad verificable sobre la lista de byes generados).
- **SC-007**: En eliminación directa con N no potencia de 2, la segunda ronda se disputa entre exactamente la menor potencia de 2 ≥ N/2 participantes tras aplicar byes en la primera ronda (cuadro equilibrado).
- **SC-008**: Un torneo se cierra automáticamente en estado "Finalizado" dentro de los 60 segundos posteriores a la confirmación del último resultado pendiente, sin necesidad de acción humana.
- **SC-009**: Un intento de iniciar un torneo con menos de 2 participantes confirmados se rechaza en el 100 % de los casos con un mensaje claro al organizador.
- **SC-010**: Un intento de modificar un parámetro bloqueado (formato, participantes, configuración general) tras iniciar el torneo se rechaza en el 100 % de los casos.

---

## Assumptions

- Los usuarios ya están autenticados mediante el sistema de autenticación de la feature 001-user-auth.
- La aplicación dispone (o dispondrá, fuera del alcance de esta feature) de un sistema de amistades que permite a los usuarios añadirse mutuamente y de un canal de notificaciones in-app. Esta feature los consume como capacidades existentes; no los construye.
- ⚠️ **[No implementado]** Se dispone de credenciales válidas para consumir la API oficial de Riot (endpoints de cuentas y de partidas). La política concreta de reintentos ante fallos transitorios de la API se tratará en la fase de diseño; funcionalmente, ante una respuesta de fallo la verificación se considera no completada y el enfrentamiento permanece pendiente. *(Esta asunción queda en suspenso hasta que la integración con la API de Riot sea implementada.)*
- ⚠️ **[No implementado]** La región/plataforma de Riot usada para buscar cuentas y partidas (EUW, NA, etc.) se determina por configuración del sistema o del usuario y no forma parte del alcance funcional de esta feature.
- Un usuario puede ser participante en más de un torneo activo simultáneamente; la restricción de desvinculación ⚠️ **[desvinculación de cuenta — no implementado]** se aplica si está participando en al menos uno.
- El desempate por "fecha de inscripción" usa el timestamp de aceptación de la invitación. Si dos inscripciones comparten el mismo instante (caso altamente improbable), se aplica como desempate estable adicional el identificador interno del participante (criterio determinista, no expuesto al usuario).
- El valor "2 participantes mínimos" aplica a ambos formatos; en eliminación directa el cuadro mínimo es 1 enfrentamiento (gran final inmediata), en round-robin es 1 enfrentamiento entre ambos.
- "Torneo activo" a efectos de bloquear la desvinculación de cuenta ⚠️ **[no implementado]** significa estados "Inscripción abierta" o "En curso" (explicitado en el prompt de entrada).