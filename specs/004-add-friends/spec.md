# Feature Specification: Añadir amigos

**Feature Branch**: `004-add-friends`
**Created**: 2026-04-28
**Status**: Draft
**Input**: User description: "Añadir amigos: buscar usuarios por nickname, ver perfiles ajenos sin opciones de edición, y gestionar la relación de amistad (enviar solicitud, ver pendiente, eliminar amigo, aceptar o rechazar solicitudes recibidas) para poder ver perfiles de amigos e invitarlos a torneos."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Buscar usuarios y visualizar su perfil (Priority: P1)

Un usuario autenticado introduce texto en un buscador y obtiene la lista de usuarios cuyo nickname contiene esa cadena (excluyéndose a sí mismo). Al pulsar sobre un resultado, accede al perfil de ese otro usuario, con la misma información que su propio perfil pero sin los controles de edición.

**Why this priority**: Es la base del descubrimiento social del producto. Sin búsqueda y visualización de perfiles ajenos, no se puede iniciar ninguna relación de amistad ni invitar a otros usuarios a un torneo. Por sí sola entrega valor (encontrar y conocer a otros jugadores) y es independientemente probable y desplegable.

**Independent Test**: Con dos o más usuarios registrados, autenticarse con uno e introducir en el buscador una subcadena presente en el nickname de los demás. Comprobar que (a) los resultados contienen a esos usuarios, (b) el propio usuario nunca aparece, (c) al pulsar un resultado se abre su perfil con la misma información que el perfil propio (nickname, foto, juegos vinculados y datos públicos del juego) pero sin opciones de edición ni acciones destructivas.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado y otros usuarios cuyos nicknames contienen el texto "user" (p. ej. `user9877`, `userMejor`), **When** introduce "user" en el buscador, **Then** el sistema muestra una lista con todos esos usuarios y excluye al propio usuario aunque su nickname también contenga "user".
2. **Given** una búsqueda con resultados, **When** el usuario pulsa sobre uno de los resultados, **Then** el sistema navega al perfil de ese usuario y muestra los mismos datos que en el perfil propio (nickname, foto, juegos vinculados y datos públicos del juego) sin controles de edición.
3. **Given** un buscador con texto que no coincide con ningún nickname, **When** el usuario ejecuta la búsqueda, **Then** el sistema muestra un estado vacío informativo, sin errores.
4. **Given** un usuario autenticado, **When** abre el perfil de otro usuario, **Then** el sistema NO muestra opciones de edición de nickname, contraseña, vinculación/desvinculación de juegos, foto de perfil ni eliminación de cuenta.

---

### User Story 2 - Enviar y gestionar solicitudes de amistad (Priority: P2)

Desde la lista de resultados de búsqueda o desde el perfil de otro usuario, el usuario autenticado ve un único botón cuyo texto y comportamiento dependen de la relación actual: "Añadir amigo" cuando no hay relación previa, "Pendiente" (sin acción) cuando ya envió solicitud y aún no se ha respondido, y "Eliminar amigo" cuando ya son amigos. El usuario receptor puede aceptar o rechazar las solicitudes recibidas desde el panel principal.

**Why this priority**: Es el núcleo funcional de la feature: convierte el descubrimiento (P1) en una relación bidireccional que habilita ver perfiles de amigos e invitarlos a torneos. Va después de P1 porque depende de la búsqueda y la visualización de perfil para tener un punto de entrada de la acción.

**Independent Test**: Con dos usuarios A y B registrados, comprobar que: (a) desde A, en el resultado de búsqueda o en el perfil de B, el botón aparece como "Añadir amigo" y al pulsarlo se envía solicitud y el botón pasa a "Pendiente"; (b) desde B, en su panel principal aparece la solicitud y puede aceptarla o rechazarla; (c) tras aceptar, el botón en ambos lados pasa a "Eliminar amigo"; (d) tras pulsar "Eliminar amigo" desde cualquiera de los dos, la amistad desaparece y el botón vuelve a "Añadir amigo"; (e) tras rechazar, no hay solicitud activa y el botón en A vuelve a "Añadir amigo".

**Acceptance Scenarios**:

1. **Given** dos usuarios A y B sin relación previa, **When** A abre el perfil o el resultado de búsqueda de B, **Then** el sistema muestra el botón "Añadir amigo".
2. **Given** A ve el botón "Añadir amigo" para B, **When** A lo pulsa, **Then** el sistema registra una solicitud pendiente de A hacia B y el botón pasa a "Pendiente" sin acción adicional para A.
3. **Given** A ya envió una solicitud a B y aún no se ha respondido, **When** A vuelve a abrir el perfil o el resultado de búsqueda de B, **Then** el sistema sigue mostrando el botón "Pendiente" sin permitir reenviar la solicitud.
4. **Given** B tiene una solicitud pendiente recibida de A, **When** B abre el panel principal, **Then** el sistema muestra la solicitud con opciones para aceptar o rechazar.
5. **Given** B tiene una solicitud pendiente recibida de A, **When** B la acepta, **Then** A y B quedan registrados como amigos y, en cualquier vista relevante para ambos, el botón pasa a "Eliminar amigo".
6. **Given** B tiene una solicitud pendiente recibida de A, **When** B la rechaza, **Then** el sistema descarta la solicitud, no crea amistad, y para A el botón vuelve a "Añadir amigo".
7. **Given** A y B ya son amigos, **When** cualquiera de los dos pulsa "Eliminar amigo" desde el perfil del otro o desde un resultado de búsqueda, **Then** el sistema elimina la amistad y el botón vuelve a "Añadir amigo" en ambos lados.
8. **Given** A y B ya son amigos, **When** A intenta enviar otra solicitud a B (por ejemplo, mediante un acceso directo), **Then** el sistema rechaza la operación, ya que el botón visible es "Eliminar amigo".

---

### Edge Cases

- **Búsqueda vacía o muy corta**: si el usuario no introduce texto o introduce solo espacios, el sistema no devuelve resultados (no se lista a todos los usuarios de la app).
- **Coincidencia con el propio nickname**: si la cadena buscada coincide con parte del propio nickname del usuario, este sigue sin aparecer en los resultados.
- **Coincidencia case-insensitive**: la búsqueda no distingue mayúsculas/minúsculas (`User` y `user` devuelven los mismos resultados).
- **Solicitud cruzada simultánea**: si A envía solicitud a B mientras B envía solicitud a A casi a la vez, el sistema debe resolver el caso sin crear dos solicitudes contradictorias y sin duplicar amistad.
- **Reenvío de solicitud rechazada**: tras rechazar una solicitud, el remitente puede volver a enviar otra solicitud más adelante (el rechazo no bloquea para siempre); la guía aquí se mantiene a las prácticas estándar y queda detallada en la sección de Asunciones.
- **Cuenta eliminada de un amigo**: si un usuario amigo elimina su cuenta (feature 003), la amistad desaparece para el otro lado y el botón deja de mostrarse para ese perfil ya inexistente.
- **Listas largas de resultados**: si la búsqueda produce un número muy grande de coincidencias, el sistema lo gestiona limitando o paginando de forma consistente para no degradar la experiencia.
- **Usuario sin foto o sin juegos vinculados**: el perfil ajeno se muestra correctamente con valores por defecto, sin errores y manteniendo la coherencia con el perfil propio.

## Requirements *(mandatory)*

### Functional Requirements

**Búsqueda de usuarios**

- **FR-001**: El sistema MUST ofrecer al usuario autenticado un buscador de usuarios por nickname accesible desde la sección de amigos del producto.
- **FR-002**: Ante una consulta no vacía, el sistema MUST devolver una lista de usuarios cuyo nickname contiene la cadena introducida (coincidencia parcial, no solo prefijo) y MUST excluir siempre al propio usuario de los resultados.
- **FR-003**: La búsqueda MUST ser insensible a mayúsculas/minúsculas.
- **FR-004**: Ante una consulta vacía o que solo contenga espacios, el sistema MUST NOT devolver la lista completa de usuarios; el resultado debe ser un estado vacío.
- **FR-005**: Cada elemento de la lista de resultados MUST ser interactivo y, al ser pulsado, MUST navegar al perfil del usuario correspondiente.

**Visualización de perfil ajeno**

- **FR-006**: El sistema MUST permitir visualizar el perfil de cualquier otro usuario seleccionado desde la lista de resultados o desde otro punto de la aplicación que enlace a un perfil.
- **FR-007**: El perfil de otro usuario MUST mostrar la misma información pública que el perfil propio (nickname, foto de perfil, juegos vinculados y sus datos públicos como nivel, servidor, rankings, maestría y últimas 5 partidas en el caso de League of Legends).
- **FR-008**: El perfil de otro usuario MUST NOT exponer ninguna opción de edición ni acciones destructivas: nickname, contraseña, vinculación/desvinculación de juegos, foto de perfil y eliminación de cuenta solo son operables desde el perfil propio.

**Gestión del estado de amistad (botón único contextual)**

- **FR-009**: Tanto en cada elemento de la lista de resultados como en el perfil de otro usuario, el sistema MUST mostrar un único botón cuyo texto y comportamiento reflejen el estado actual de la relación entre el usuario autenticado y el usuario objetivo.
- **FR-010**: Si NO existe relación previa entre los dos usuarios, el botón MUST mostrar "Añadir amigo" y, al pulsarlo, MUST registrar una solicitud pendiente del usuario autenticado hacia el usuario objetivo.
- **FR-011**: Si el usuario autenticado YA envió una solicitud al usuario objetivo y esta sigue sin respuesta, el botón MUST mostrar "Pendiente" y MUST NOT desencadenar acciones al ser pulsado (estado informativo).
- **FR-012**: Si los dos usuarios YA son amigos, el botón MUST mostrar "Eliminar amigo" y, al pulsarlo, MUST eliminar la amistad de forma simétrica (deja de existir en ambas direcciones).
- **FR-013**: El sistema MUST garantizar que el usuario autenticado no puede enviar una solicitud de amistad a un usuario que ya es amigo o con el que ya tiene una solicitud pendiente; si por cualquier vía se intenta, la operación MUST ser rechazada.
- **FR-014**: El sistema MUST impedir que un usuario se envíe una solicitud de amistad a sí mismo.

**Solicitudes recibidas (panel principal)**

- **FR-015**: El sistema MUST mostrar al usuario autenticado, en el panel principal, las solicitudes de amistad recibidas pendientes con la opción de aceptarlas o rechazarlas.
- **FR-016**: Al aceptar una solicitud, el sistema MUST crear la amistad entre los dos usuarios de forma simétrica y MUST eliminar la solicitud pendiente; a partir de ese momento el botón en cualquier vista relevante MUST reflejar el estado "Eliminar amigo".
- **FR-017**: Al rechazar una solicitud, el sistema MUST descartar la solicitud sin crear amistad; el botón visible para el remitente MUST volver a "Añadir amigo".

**Coherencia y reglas transversales**

- **FR-018**: La amistad MUST ser simétrica: si A es amigo de B, B también lo es de A; cualquier vista del estado de la relación MUST reflejarlo en ambos lados.
- **FR-019**: Todas las acciones de búsqueda, visualización de perfil ajeno y gestión de amistad MUST requerir autenticación válida del usuario; las peticiones realizadas en nombre de otro usuario MUST ser rechazadas.
- **FR-020**: Si un usuario que era amigo deja de existir (por ejemplo, eliminó su cuenta según la feature 003), la relación de amistad MUST quedar deshecha automáticamente y el sistema MUST manejar las vistas afectadas sin error.
- **FR-021**: El sistema MUST manejar de forma consistente solicitudes cruzadas (A → B y B → A en ventana próxima), evitando estados duplicados o contradictorios; el resultado final esperado es una única amistad simétrica si ambos pasan por aceptación, o el estado pendiente correcto si solo una solicitud se materializa antes que la otra.

### Key Entities *(include if feature involves data)*

- **Usuario (existente)**: entidad ya definida en 001-user-auth y enriquecida en 003-edit-profile (foto, juegos vinculados, datos públicos del juego). Esta feature solo lee información pública del usuario y no modifica sus atributos propios.
- **Solicitud de amistad**: representa una petición pendiente desde un usuario remitente hacia un usuario destinatario. Atributos lógicos: remitente, destinatario, fecha de creación, estado (pendiente). Las solicitudes aceptadas se transforman en una relación de amistad y dejan de existir como solicitud; las rechazadas se descartan.
- **Amistad**: relación simétrica entre dos usuarios. Una vez establecida, ambos usuarios se ven mutuamente como "amigos" hasta que uno la elimine. No tiene "remitente" ni "destinatario" desde el punto de vista funcional.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Al introducir una cadena en el buscador, el usuario obtiene los resultados pertinentes (todos los nicknames que contienen la cadena, sin incluirse a sí mismo) en menos de 2 segundos en condiciones normales.
- **SC-002**: En el 100% de las búsquedas, el propio usuario nunca aparece en los resultados, aunque su nickname contenga la cadena buscada.
- **SC-003**: En el 100% de las visitas al perfil de otro usuario, no se expone ninguna opción de edición o acción destructiva propia del perfil; un usuario no puede modificar a otro desde la vista del perfil ajeno.
- **SC-004**: El botón de relación refleja el estado correcto ("Añadir amigo", "Pendiente" o "Eliminar amigo") en el 100% de los casos al abrir un perfil o un resultado de búsqueda.
- **SC-005**: El 100% de los intentos de enviar una solicitud a un usuario que ya es amigo o tiene solicitud pendiente son rechazados por el sistema, sin crear duplicados.
- **SC-006**: Tras aceptar una solicitud de amistad desde el panel principal, ambos usuarios pueden verse como amigos (botón "Eliminar amigo") sin necesidad de recargar la sesión, en menos de 5 segundos desde la aceptación.
- **SC-007**: Tras rechazar una solicitud, no queda ninguna solicitud activa entre los dos usuarios y el remitente vuelve a ver "Añadir amigo" sin estados intermedios incoherentes.
- **SC-008**: Tras eliminar una amistad, ningún rastro de la relación queda visible para ninguno de los dos usuarios y cualquiera de ellos puede volver a iniciar el flujo "Añadir amigo".

## Assumptions

- El "panel principal" desde el que se aceptan o rechazan las solicitudes recibidas es la pantalla de inicio post-login del producto; su diseño concreto es ajeno a esta feature, que solo aporta el bloque de "solicitudes pendientes". El equipo de producto definirá la ubicación visual exacta dentro de ese panel.
- La búsqueda es insensible a mayúsculas/minúsculas y opera por coincidencia parcial sobre el nickname (no por prefijo estricto), siguiendo el patrón habitual de búsqueda social. Detalles como la longitud mínima de consulta o la paginación se concretarán en la planificación técnica.
- El número de resultados expuestos por búsqueda se limita a un valor razonable (por ejemplo, decenas) para preservar la experiencia de usuario; el límite exacto y la estrategia de paginación o "ver más" se decidirán en planificación.
- Tras un rechazo de solicitud, el remitente puede volver a enviar otra solicitud más adelante; no se introduce un mecanismo de bloqueo persistente en esta feature (un sistema de "bloquear usuario" queda fuera de alcance).
- Las solicitudes de amistad no caducan por tiempo en esta versión: permanecen pendientes hasta que el destinatario las acepte o rechace, o hasta que cualquiera de los dos usuarios desaparezca.
- Cuando un usuario elimina su cuenta (feature 003), las amistades en las que participaba dejan de existir para los otros usuarios; los registros históricos de torneos siguen las reglas definidas en la feature 003.
- La invitación a torneos a partir de los amigos no forma parte de esta feature: aquí solo se habilita la relación de amistad y el acceso al perfil del amigo. La integración con la feature 002-tournament-management se materializa en una iteración posterior reutilizando las amistades creadas.
- La autenticación, el manejo de sesiones y la protección de los endpoints reutilizan los mecanismos definidos en 001-user-auth; esta feature no redefine reglas de seguridad de sesión.
- La búsqueda y los listados de solicitudes pendientes se diseñan pensando en un cliente web autenticado; el soporte específico para móvil queda fuera del alcance explícito de esta feature.
