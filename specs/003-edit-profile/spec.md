# Feature Specification: Editar perfil de usuario

**Feature Branch**: `003-edit-profile`
**Created**: 2026-04-25
**Status**: Draft
**Input**: User description: "Editar perfil: el usuario logueado puede cambiar nickname (único), contraseña (con restricciones), vincular/desvincular videojuegos (League of Legends vía API de Riot, sin guardar credenciales), foto de perfil (con límite de peso y recorte) y eliminar cuenta (con confirmación, bloqueado mientras participe en torneo). Visualización del perfil con datos públicos del juego vinculado: nivel, servidor, Ranked Solo/Dúo, Ranked Flex, maestría de campeones y últimas 5 partidas."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Visualizar el perfil y editar datos básicos (Priority: P1)

Un usuario autenticado entra en la sección "Perfil", ve sus datos actuales (nickname, foto, juegos vinculados) y puede modificar su nickname, su contraseña y su foto de perfil desde la misma sección. El sistema valida los cambios (unicidad de nickname, restricciones de contraseña, peso y formato de foto) y confirma la actualización.

**Why this priority**: Es la base del producto en cuanto a identidad del usuario. Sin la sección "Perfil" y la edición de datos básicos, el usuario no puede personalizar su cuenta ni resolver problemas comunes (cambio de contraseña, nickname). Es la funcionalidad mínima viable de esta feature.

**Independent Test**: Con un usuario registrado y autenticado, acceder a "Perfil" y comprobar que: (a) se muestran sus datos actuales; (b) puede cambiar nickname a uno libre y el cambio persiste; (c) puede cambiar contraseña con una válida y al cerrar sesión y volver a entrar funciona la nueva; (d) puede subir una foto válida y se guarda recortada. Cada acción funciona aunque las demás no estén disponibles.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado, **When** accede a la sección "Perfil", **Then** el sistema muestra su nickname, su foto de perfil actual y la lista de videojuegos vinculados (si los hay).
2. **Given** un usuario en "Perfil", **When** introduce un nickname nuevo que no está en uso por otro usuario y confirma, **Then** el sistema actualiza el nickname y muestra confirmación.
3. **Given** un usuario en "Perfil", **When** intenta cambiar su nickname a uno ya utilizado por otro usuario, **Then** el sistema rechaza el cambio con un mensaje indicando que el nickname no está disponible y conserva el nickname anterior.
4. **Given** un usuario en "Perfil", **When** introduce una contraseña nueva que cumple las restricciones, **Then** el sistema actualiza la contraseña y al cerrar sesión y volver a iniciar sesión, la nueva contraseña funciona y la anterior no.
5. **Given** un usuario en "Perfil", **When** intenta cambiar su contraseña por una que no cumple las restricciones, **Then** el sistema rechaza el cambio indicando qué restricciones no se cumplen.
6. **Given** un usuario en "Perfil", **When** sube una imagen dentro del límite de peso aceptado, **Then** el sistema la almacena recortada en formato cuadrado y la muestra como su foto de perfil.
7. **Given** un usuario en "Perfil", **When** sube una imagen que supera el límite de peso, **Then** el sistema rechaza la subida indicando el límite máximo permitido.

---

### User Story 2 - Vincular y desvincular cuenta de League of Legends (Priority: P2)

Un usuario autenticado abre "Perfil" y vincula su cuenta de League of Legends introduciendo sus credenciales del videojuego. El sistema utiliza esas credenciales para consultar la API de Riot, obtiene los datos públicos de la cuenta y, una vez recuperados, descarta las credenciales sin guardarlas. A partir de ese momento, el sistema muestra dentro del perfil información pública del juego (nivel, servidor, Ranked Solo/Dúo, Ranked Flex, maestría de campeones y últimas 5 partidas). El usuario también puede desvincular el juego, salvo que esté participando en un torneo activo de ese juego.

**Why this priority**: Es el diferenciador funcional respecto a un perfil genérico. La vinculación de cuenta es además dependencia transversal de la feature de torneos (002), por lo que su disponibilidad desbloquea valor más allá de esta sección. Aun así, no es bloqueante para que el usuario pueda usar el resto del perfil.

**Independent Test**: Con un usuario autenticado y unas credenciales válidas de Riot, comprobar que: (a) tras vincular, el perfil muestra los datos públicos del juego; (b) las credenciales no quedan accesibles desde el cliente ni en almacenamiento persistente; (c) si el usuario no está en ningún torneo activo, puede desvincular y la información del juego desaparece del perfil; (d) si está participando en un torneo activo del juego, el sistema impide la desvinculación.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado sin League of Legends vinculado, **When** introduce credenciales válidas de Riot y confirma la vinculación, **Then** el sistema obtiene los datos públicos a través de la API de Riot, vincula la cuenta y descarta las credenciales sin almacenarlas.
2. **Given** un usuario autenticado, **When** introduce credenciales incorrectas para vincular Riot, **Then** el sistema rechaza la vinculación con un mensaje de error genérico que no distingue entre identificador inválido y contraseña incorrecta.
3. **Given** un usuario con League of Legends vinculado, **When** abre la sección "Perfil", **Then** el sistema muestra nivel, servidor, Ranked Solo/Dúo, Ranked Flex, maestría de campeones y un listado de las 5 últimas partidas.
4. **Given** un usuario con League of Legends vinculado y sin participación activa en ningún torneo de ese juego, **When** pulsa "Desvincular", **Then** el sistema elimina el vínculo y deja de mostrar los datos del juego en el perfil.
5. **Given** un usuario con League of Legends vinculado y al menos un torneo activo en el que participa, **When** intenta desvincular, **Then** el sistema impide la desvinculación con un mensaje que indica el motivo.
6. **Given** un usuario con League of Legends vinculado, **When** la API de Riot no responde al cargar el perfil, **Then** el sistema indica que los datos del juego no están disponibles temporalmente y permite seguir usando el resto del perfil.

---

### User Story 3 - Eliminar la cuenta de forma controlada (Priority: P3)

Un usuario autenticado decide eliminar su cuenta de forma definitiva. Desde "Perfil", solicita la eliminación, el sistema le pide una confirmación explícita escribiendo un texto concreto y, solo si la confirmación es exacta y el usuario no participa en ningún torneo activo, procede a eliminar la cuenta. El usuario queda desconectado y todos sus datos personales asociados quedan eliminados.

**Why this priority**: Es una acción destructiva e irreversible que el usuario invocará rara vez. Es necesaria por requisitos legales y de privacidad, pero no aporta valor diario. Va después de las funciones cotidianas para no introducir riesgo en el flujo principal antes de tener bien probados los flujos de uso habitual.

**Independent Test**: Con un usuario autenticado, verificar que: (a) sin participar en ningún torneo activo, tras escribir el texto de confirmación exacto se elimina la cuenta y queda desconectado; (b) si introduce un texto de confirmación distinto, no se elimina; (c) si participa en algún torneo activo, el sistema rechaza la eliminación con un mensaje claro.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado sin participación activa en ningún torneo, **When** solicita eliminar su cuenta y escribe correctamente el texto de confirmación, **Then** el sistema elimina la cuenta, cierra la sesión y los datos personales del usuario dejan de ser recuperables.
2. **Given** un usuario que solicita eliminar su cuenta, **When** introduce un texto de confirmación distinto al exigido, **Then** el sistema cancela la eliminación y mantiene la cuenta intacta.
3. **Given** un usuario que participa en al menos un torneo activo, **When** intenta eliminar su cuenta, **Then** el sistema rechaza la operación e indica que debe abandonar o esperar a la finalización de los torneos en los que participa.

---

### Edge Cases

- **Nickname idéntico al actual**: si el usuario "cambia" el nickname al que ya tiene, el sistema acepta sin error (sin tratarlo como conflicto de unicidad).
- **Carrera de unicidad de nickname**: si dos usuarios intentan reclamar el mismo nickname libre a la vez, solo uno lo obtiene; el otro recibe el error de nickname no disponible.
- **Subida de foto en formato no soportado**: el sistema rechaza la subida indicando los formatos admitidos.
- **Desvinculación cuando hay torneos finalizados**: si la participación del usuario en torneos de ese juego está toda finalizada, la desvinculación se permite (la restricción solo aplica a torneos activos).
- **Cambio de contraseña con sesiones activas en otros dispositivos**: tras un cambio de contraseña, las sesiones existentes deben dejar de ser válidas (consistente con la práctica del producto en autenticación).
- **API de Riot caída durante la vinculación**: la vinculación falla y se informa de error temporal; no se vincula la cuenta a medias.
- **Cancelación de eliminación**: el usuario puede cerrar el diálogo de confirmación en cualquier momento sin consecuencias.
- **Eliminación de cuenta con datos en torneos finalizados**: el sistema debe poder eliminar la cuenta conservando la integridad histórica de torneos cerrados (resultado/clasificación) anonimizando o conservando referencias mínimas, según la práctica habitual del producto.

## Requirements *(mandatory)*

### Functional Requirements

**Sección "Perfil" y visualización**

- **FR-001**: El sistema MUST exponer una sección "Perfil" accesible para cualquier usuario autenticado que agrupe la visualización y todas las opciones de edición de los datos del propio usuario.
- **FR-002**: El sistema MUST mostrar en el perfil del usuario su nickname actual, su foto de perfil y la lista de videojuegos vinculados.
- **FR-003**: Para cada juego vinculado, el sistema MUST mostrar la información pública obtenida del proveedor del juego. Para League of Legends, MUST incluir: nivel, servidor, Ranked Solo/Dúo, Ranked Flex, maestría de campeones y las últimas 5 partidas.

**Edición de nickname**

- **FR-004**: El sistema MUST permitir al usuario autenticado cambiar su propio nickname desde "Perfil".
- **FR-005**: El sistema MUST garantizar que dos usuarios distintos no puedan tener el mismo nickname; cualquier intento de fijar un nickname ya utilizado MUST ser rechazado con un mensaje informativo y MUST conservar el nickname anterior.
- **FR-006**: Si el nuevo nickname coincide con el actual del propio usuario, el sistema MUST tratarlo como operación válida sin error.

**Edición de contraseña**

- **FR-007**: El sistema MUST permitir al usuario autenticado cambiar su propia contraseña desde "Perfil".
- **FR-008**: El sistema MUST aplicar a la nueva contraseña las mismas restricciones de complejidad utilizadas en el registro y restablecimiento (definidas en la feature 001-user-auth).
- **FR-009**: Tras un cambio de contraseña exitoso, el sistema MUST invalidar las sesiones activas distintas de la actual de modo que requieran iniciar sesión nuevamente con la contraseña nueva.

**Vinculación y desvinculación de videojuegos**

- **FR-010**: El sistema MUST permitir al usuario vincular su cuenta de League of Legends desde "Perfil" introduciendo las credenciales del videojuego (no las de la aplicación).
- **FR-011**: El sistema MUST utilizar la API oficial de Riot para autenticar y obtener los datos públicos de la cuenta del videojuego.
- **FR-012**: El sistema MUST NOT almacenar las credenciales del videojuego ni de forma persistente ni en logs ni accesibles desde el navegador del usuario; tras completar la vinculación, las credenciales MUST ser descartadas.
- **FR-013**: Cuando la vinculación con la API de Riot falle por credenciales inválidas, el sistema MUST devolver un mensaje de error genérico que NO distinga entre identificador incorrecto y contraseña incorrecta del videojuego.
- **FR-014**: El sistema MUST permitir al usuario desvincular un videojuego previamente vinculado, salvo cuando el usuario participe en un torneo activo de ese videojuego, en cuyo caso MUST rechazar la desvinculación con un mensaje que explique el motivo.
- **FR-015**: Para esta versión, el único videojuego disponible para vincular MUST ser League of Legends; la sección debe ser extensible a futuros videojuegos sin rediseñar la experiencia del usuario.
- **FR-016**: El sistema MUST manejar de forma controlada la indisponibilidad temporal de la API de Riot al cargar el perfil, indicando que los datos del juego no están disponibles momentáneamente sin afectar al resto de la sección.

**Foto de perfil**

- **FR-017**: El sistema MUST permitir al usuario subir una nueva foto de perfil en formatos de imagen comunes (JPEG, PNG, WebP).
- **FR-018**: El sistema MUST rechazar imágenes que superen el límite máximo de peso definido por la plataforma e informar del límite al usuario.
- **FR-019**: El sistema MUST aplicar un recorte cuadrado a la imagen antes de almacenarla, asegurando una representación uniforme del avatar en toda la aplicación.
- **FR-020**: El sistema MUST permitir mantener una foto por defecto cuando el usuario no haya subido ninguna.

**Eliminación de cuenta**

- **FR-021**: El sistema MUST ofrecer al usuario una acción de eliminación de cuenta dentro de "Perfil".
- **FR-022**: Antes de proceder, el sistema MUST exigir al usuario que escriba una cadena de confirmación exacta (por ejemplo, su nickname o un texto fijo predefinido); cualquier desviación MUST cancelar la operación.
- **FR-023**: El sistema MUST impedir la eliminación de la cuenta mientras el usuario participe en al menos un torneo activo, devolviendo un mensaje que indique cómo proceder.
- **FR-024**: Tras una eliminación válida, el sistema MUST eliminar los datos personales del usuario, cerrar la sesión y dejar la cuenta como no recuperable; los datos históricos de torneos cerrados MUST mantener integridad referencial mínima (anonimización si procede).

**Restricciones de seguridad transversales**

- **FR-025**: El sistema MUST NOT exponer tokens de sesión de la aplicación en almacenamiento accesible desde JavaScript del navegador; los tokens MUST estar protegidos siguiendo la práctica establecida en la feature 001-user-auth.
- **FR-026**: Todos los endpoints de edición de perfil MUST requerir autenticación válida del propio usuario y rechazar peticiones sobre el perfil de otros usuarios.

### Key Entities *(include if feature involves data)*

- **Usuario (existente)**: entidad ya definida en 001-user-auth. Esta feature añade/usa los atributos: foto de perfil (referencia al recurso de imagen) y la relación con cuentas de juego vinculadas. La gestión de credenciales de la app sigue siendo la de 001.
- **Cuenta de juego vinculada**: representa la asociación entre un usuario y una cuenta externa de un videojuego. Atributos clave (sin detalles de implementación): identificador externo del jugador en el videojuego, servidor/región, fecha de vinculación. NO contiene credenciales del videojuego.
- **Datos públicos del juego** (League of Legends): instantánea de información pública consultada al proveedor: nivel, servidor, ranking Solo/Dúo, ranking Flex, maestría de campeones y últimas 5 partidas. Su persistencia (caché) o consulta directa es decisión de implementación posterior.
- **Foto de perfil**: imagen asociada a un usuario, en formato cuadrado y dentro del límite de peso permitido. Una foto por usuario; se sustituye al subir una nueva.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario autenticado puede completar cualquiera de las acciones básicas de perfil (cambiar nickname, cambiar contraseña, cambiar foto) en menos de 60 segundos desde que abre la sección "Perfil", incluyendo tiempo de validación y confirmación.
- **SC-002**: El 100% de los intentos de cambio a un nickname ya usado por otro usuario son rechazados con un mensaje claro, sin que el nickname original del usuario se altere.
- **SC-003**: En el 100% de las vinculaciones de cuenta de videojuego, las credenciales introducidas dejan de existir en el sistema (memoria, almacenamiento, logs y respuestas al cliente) en cuanto la vinculación finaliza, exitosa o no.
- **SC-004**: El 100% de los intentos de desvincular un juego mientras se participa en un torneo activo son rechazados, evitando huérfanos en torneos en curso.
- **SC-005**: El 100% de los intentos de eliminar la cuenta sin la confirmación textual exacta son cancelados sin alterar los datos del usuario.
- **SC-006**: El 100% de los intentos de eliminar la cuenta mientras se participa en un torneo activo son rechazados con mensaje informativo.
- **SC-007**: El usuario percibe los datos públicos del juego (nivel, servidor, rankings, maestría, últimas 5 partidas) cargados o con un mensaje claro de "no disponible" en menos de 5 segundos al abrir el perfil bajo condiciones normales.
- **SC-008**: Los mensajes de error de vinculación con Riot por credenciales inválidas son indistinguibles entre identificador incorrecto y contraseña incorrecta en el 100% de los casos.

## Assumptions

- Las restricciones de complejidad de la nueva contraseña son las mismas definidas en la feature 001-user-auth (no se redefinen aquí). En particular, se asume coherencia con esa feature en validaciones, mensajes y políticas de invalidación de sesiones tras un cambio.
- El concepto de "torneo activo" se hereda de la feature 002-tournament-management: incluye torneos en estados previos a su finalización (por ejemplo, "Borrador", "Inscripción abierta", "En curso") y excluye torneos finalizados o cancelados. La definición exacta es la de 002.
- El límite de peso de la foto de perfil sigue prácticas estándar de la industria (en torno a 5 MB) y los formatos admitidos son JPEG, PNG y WebP. El valor concreto y los formatos se confirmarán durante la planificación técnica.
- El recorte cuadrado se realiza en el cliente o en el servidor según convenga a la implementación; lo que la feature exige es que la imagen final almacenada y servida sea cuadrada.
- La confirmación textual de eliminación de cuenta consiste en escribir el propio nickname del usuario, criterio estándar y libre de traducción ambigua. La cadena exacta puede ajustarse en planificación si se decide otra convención (por ejemplo, "ELIMINAR").
- La sesión actual del usuario se preserva tras un cambio de contraseña, mientras que las demás sesiones quedan invalidadas, siguiendo el patrón de 001-user-auth.
- La caché o frescura de los datos públicos del juego (cada cuánto se consulta a Riot) es una decisión de planificación técnica y no impacta los criterios de aceptación de esta feature.
- La eliminación de cuenta no implica eliminar de forma destructiva los registros históricos de torneos cerrados; la anonimización (sustituir referencias al usuario por un valor neutro) es la práctica asumida para mantener la integridad de clasificaciones pasadas.
- La feature asume disponibilidad de la API oficial de Riot y de sus datos públicos para los campos requeridos (nivel, servidor, Ranked Solo/Dúo, Ranked Flex, maestría de campeones, últimas 5 partidas).
- La sección "Perfil" se diseña pensando en su uso desde un cliente web autenticado; el soporte específico para móvil queda fuera del alcance explícito de esta feature.
