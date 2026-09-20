# BITACORA-IA.md

## Propósito

Registrar el uso de herramientas de inteligencia artificial durante el desarrollo del proyecto, incluyendo las propuestas obtenidas, las alternativas consideradas y las decisiones tomadas por la estudiante.

La inteligencia artificial se utiliza como herramienta de apoyo para el análisis, diseño, revisión y desarrollo, pero las decisiones finales del proyecto son tomadas por la estudiante.

---

## Sesión 1 — Análisis del problema y definición inicial del alcance

### Objetivo

Comprender el problema planteado, identificar las reglas de negocio, delimitar el alcance y establecer las primeras decisiones de diseño antes de comenzar la implementación.

### Uso de IA

Se utilizó ChatGPT como herramienta de apoyo para:

* Analizar el problema planteado en el enunciado.
* Identificar entidades y relaciones posibles.
* Cuestionar decisiones iniciales.
* Explorar alternativas de modelado.
* Identificar casos límite.
* Diferenciar requisitos del sistema de suposiciones sobre el funcionamiento del restaurante.
* Revisar el alcance para evitar implementar funcionalidades innecesarias.

### Proceso de decisión

El proceso seguido no consistió en aceptar directamente una solución propuesta por la IA.

La estudiante planteó inicialmente una interpretación del funcionamiento del restaurante y posibles funcionalidades. A partir de estas propuestas, se discutieron alternativas y se identificaron aspectos que podían aumentar innecesariamente el alcance.

Entre las decisiones analizadas estuvieron:

* Manejar inventario mediante cantidades detalladas o mediante disponibilidad simplificada.
* Registrar o no el número de comensales.
* Asignar físicamente cocineros a pedidos o utilizar únicamente una estimación de carga.
* Representar los pedidos directamente asociados a una mesa o mediante una sesión.
* Manejar una cuenta por pedido o una cuenta asociada a la sesión de la mesa.
* Permitir que un mismo ítem pueda distribuirse entre diferentes pagos.

### Decisiones tomadas

La estudiante decidió:

1. Utilizar cantidades abstractas de ingredientes para controlar disponibilidad sin construir un sistema completo de inventario.
2. No registrar el número de comensales.
3. Utilizar sesiones para agrupar los pedidos de una mesa.
4. Permitir múltiples pedidos durante una misma sesión.
5. Representar la complejidad mediante un puntaje de carga de preparación.
6. Generar una recomendación de cantidad de cocineros sin realizar asignación de personal.
7. Manejar los estados de preparación individualmente por ítem.
8. Permitir dividir la cuenta entre diferentes pagos.
9. Permitir distribuir cantidades de un mismo ítem entre diferentes pagos.
10. Mantener los pagos como registros internos, sin implementar procesamiento electrónico real.

### Reflexión

Durante esta sesión se identificó la importancia de distinguir entre una funcionalidad necesaria para resolver el problema y una funcionalidad que simplemente podría existir en un restaurante real.

También se identificó que algunas decisiones inicialmente consideradas podían aumentar considerablemente el alcance del proyecto sin aportar directamente al problema principal.

---

## Próxima sesión

Convertir las decisiones funcionales tomadas durante esta sesión en un modelo de datos y revisar las relaciones entre las entidades antes de comenzar la implementación.

---

## Sesión 2 --- Consolidación del modelo funcional y diseño relacional

### Objetivo

Revisar las decisiones tomadas durante la primera sesión, resolver casos límite y transformar el modelo conceptual inicial en una estructura relacional coherente antes de seleccionar la tecnología de implementación.

### Uso de IA

Se utilizó ChatGPT como herramienta de apoyo para:

- Revisar las entidades y relaciones identificadas anteriormente.
- Cuestionar si determinados datos debían almacenarse o derivarse.
- Analizar la representación de unidades repetidas de un mismo plato.
- Revisar la relación entre recetas actuales y pedidos históricos.
- Explorar restricciones de integridad que podrían ser garantizadas desde la base de datos.
- Identificar posibles inconsistencias y redundancias en el modelo.
- Revisar el flujo de reserva y devolución de ingredientes.
- Comprobar que el modelo permitiera cumplir la división de cuentas y pagos parciales.

### Decisiones tomadas durante la sesión

#### 1. Trazabilidad del mesero

Se decidió registrar el mesero responsable en `Sesion` mediante una relación con `Usuario`.

La sesión tendrá:

mesero_id FK → Usuario.id

Esto permite saber quién atendió una mesa durante una sesión sin repetir el dato en cada pedido.

#### 2. Estado de `Pedido` derivado

Se decidió no almacenar físicamente `Pedido.estado`.

El estado operativo del pedido se deriva de los estados de sus `ItemPedido`.

Esto evita tener dos fuentes de verdad que podrían quedar inconsistentes.

#### 3. Estados de `ItemPedido`

Los estados definidos son:

EN_COLA
EN_PREPARACION
LISTO
CANCELADO

El flujo normal es:

EN_COLA → EN_PREPARACION → LISTO

La cancelación solamente puede realizarse desde `EN_COLA`.

#### 4. Individualización de los ítems

Se decidió que cada unidad solicitada será un registro independiente de `ItemPedido`.

Por ejemplo, tres hamburguesas se representan como tres ítems, en lugar de un único ítem con `cantidad = 3`.

La interfaz podrá agrupar visualmente unidades iguales para facilitar la operación en cocina.

### Motivo

Esta decisión permite que cada unidad tenga su propio estado de preparación y facilita asignar unidades concretas a diferentes pagos.

#### 5. Precio histórico del pedido

`ItemPedido` conserva `precio_unitario`, tomado del precio del `Plato` al momento de solicitarlo.

De esta forma, un cambio posterior de precio del plato no modifica el valor de pedidos anteriores.

#### 6. Composición actual del plato

Se definió `ComposicionPlato` como representación de la receta actual:

plato_id
ingrediente_id
cantidad_requerida

La cantidad requerida representa una unidad abstracta de consumo definida por el restaurante.

#### 7. Fotografía de la composición del pedido

Se definió `ComposicionItemPedido` para conservar la composición de ingredientes comprometida para cada unidad específica del pedido.

Esto permite que una modificación posterior de la receta del plato no altere retrospectivamente la composición de un pedido ya realizado.

También permite saber qué cantidades deben devolverse si el ítem se cancela mientras está `EN_COLA`.

#### 8. Momento de reserva de ingredientes

Se decidió que los ingredientes no se descuentan mientras el mesero está construyendo el pedido.

Al enviar el pedido a cocina:

1. se valida nuevamente la disponibilidad;
2. se registra la composición de cada ítem;
3. se descuentan las cantidades disponibles;
4. los ítems pasan a `EN_COLA`.

Esto representa una reserva mediante la disminución de `cantidad_disponible`, sin crear una entidad separada de inventario reservado.

#### 9. Cuenta asociada a la sesión

Se confirmó que una `Sesion` posee una única `Cuenta` que reúne todos los pedidos de esa atención.

La cuenta no almacena el total: este se calcula a partir de los `ItemPedido` no cancelados.

#### 10. Estado de `Cuenta` derivado

Se decidió no almacenar físicamente el estado de la cuenta.

Una cuenta se considera pendiente mientras exista algún `ItemPedido` no cancelado sin asignación de pago.

Se considera pagada cuando todas las unidades no canceladas han sido asignadas a pagos.

#### 11. Estado de `Sesion` derivado

Se decidió no almacenar `estado` en `Sesion`.

La sesión se considera:

ACTIVA  → fecha_hora_fin IS NULL
CERRADA → fecha_hora_fin IS NOT NULL

Antes de cerrar una sesión, la lógica de negocio deberá comprobar que la cuenta esté completamente pagada.

#### 12. División de pagos

Se confirmó que los pagos se registrarán mediante:

Cuenta → Pago → AsignacionPago → ItemPedido

No se almacena un monto independiente para `Pago`.

Como cada `ItemPedido` representa una unidad, un mismo ítem individual no puede dividirse entre varios pagos.

Un pago sí puede incluir unidades provenientes de diferentes pedidos de la misma cuenta.

#### 13. Restricciones de integridad identificadas

Se identificaron restricciones que deberán reflejarse en el modelo y, cuando la tecnología lo permita, también en la base de datos:

- `ComposicionPlato(plato_id, ingrediente_id)` debe ser único.
- `ComposicionItemPedido(item_pedido_id, ingrediente_id)` debe ser único.
- Una `Sesion` debe tener una única `Cuenta`.
- Una unidad de `ItemPedido` solo puede estar asignada a un `Pago`.
- Una `Mesa` no debe tener más de una `Sesion` activa simultáneamente.
- Las claves foráneas deberán garantizar las relaciones entre las entidades.

Las transiciones de estados y las reglas que dependen de consultas entre
varias tablas deberán controlarse principalmente mediante la lógica de
negocio.

### Modelo relacional consolidado

USUARIO
- id PK
- nombre
- rol
- activo

MESA
- id PK
- numero

SESION
- id PK
- fecha_hora_inicio
- fecha_hora_fin
- mesa_id FK
- mesero_id FK

PEDIDO
- id PK
- fecha_hora_creacion
- observaciones
- sesion_id FK

ITEM_PEDIDO
- id PK
- precio_unitario
- estado
- pedido_id FK
- plato_id FK

PLATO
- id PK
- nombre
- precio
- puntaje_carga_preparacion
- activo

INGREDIENTE
- id PK
- nombre
- cantidad_disponible
- activo

COMPOSICION_PLATO
- id PK
- plato_id FK
- ingrediente_id FK
- cantidad_requerida

COMPOSICION_ITEM_PEDIDO
- id PK
- item_pedido_id FK
- ingrediente_id FK
- cantidad

CUENTA
- id PK
- sesion_id FK

PAGO
- id PK
- fecha_hora
- cuenta_id FK

ASIGNACION_PAGO
- id PK
- pago_id FK
- item_pedido_id FK

### Reflexión

La segunda sesión permitió identificar que varias propiedades inicialmente pensadas como atributos podían derivarse de otros datos.

Se decidió evitar el almacenamiento redundante de los estados de `Pedido`, `Cuenta` y `Sesion`.

También se comprobó que individualizar las unidades de `ItemPedido` aumenta la trazabilidad y simplifica la división de la cuenta, mientras que la interfaz podrá encargarse de agrupar visualmente los ítems para no trasladar esa complejidad al usuario de cocina.

La revisión del modelo también permitió separar dos conceptos que inicialmente podían confundirse: la receta actual de un plato (`ComposicionPlato`) y la composición de ingredientes comprometida para un pedido concreto (`ComposicionItemPedido`).

### Estado al cierre de la sesión

El modelo relacional conceptual se considera suficientemente consolidado para pasar a la siguiente etapa.

Todavía no se ha seleccionado la tecnología de backend, frontend ni base de datos.

### Próxima sesión

Seleccionar y justificar la tecnología de implementación, revisar alternativas y definir la estructura inicial del proyecto.

La decisión tecnológica correspondiente deberá documentarse mediante un ADR.

---

## Sesión 3 — Adopción tecnológica y modelo de datos inicial

### Objetivo y uso de IA

La estudiante solicitó a Codex revisar los documentos previos, comprobar
el repositorio y el entorno, proponer un trabajo incremental e implementar
primero la estructura ejecutable y después el modelo relacional. Codex se
utilizó efectivamente para proponer y editar código y documentación, crear
la migración del modelo y preparar pruebas. La estudiante confirmó el
alcance y autorizó cada incremento; la revisión y comprensión final del
código siguen siendo su responsabilidad.

### Decisiones confirmadas por la estudiante

- Adoptar un monolito modular con React, JavaScript y Vite en `frontend/`,
  Django REST Framework en `backend/` y PostgreSQL, todo en un repositorio.
- Usar autenticación básica de Django con los roles `ADMIN`, `MESERO` y
  `COCINERO`, sin autenticación avanzada.
- Construir temporalmente la selección del pedido en React y persistirla
  únicamente al enviarla a cocina. El envío deberá ser atómico: si falta
  algún ingrediente, se rechazará el pedido completo.
- Rechazar pedidos vacíos y cantidades negativas; representar precios y
  cantidades de ingredientes con decimales. Cada unidad solicitada sigue
  siendo un `ItemPedido` independiente, por lo que el número de unidades
  es entero.

La decisión inicial de la sesión 1 de dividir cantidades de un mismo ítem
entre pagos fue **sustituida durante la sesión 2**: desde entonces, cada
unidad se representa como un `ItemPedido` independiente y una unidad
individual puede asignarse a un solo pago. Se conserva el registro de la
decisión inicial para mostrar la evolución del diseño.

### Propuestas técnicas incorporadas

Codex propuso separar `frontend/` y `backend/`, configurar la conexión
local mediante variables de entorno y un archivo `.env` ignorado por Git,
y usar la aplicación Django `restaurant` para las doce entidades del
modelo. Para integrar la autenticación ya migrada de Django, propuso
vincular `Usuario` uno a uno con `auth.User`; `Usuario.activo` lee
`auth.User.is_active` y evita duplicar el valor.

Se eligieron `DecimalField(max_digits=12, decimal_places=2)` para precios
y `DecimalField(max_digits=12, decimal_places=3)` para porciones abstractas
de ingredientes. La base incluye claves foráneas, relaciones uno a uno,
unicidades de composiciones y asignaciones, y un índice único condicional
que impide dos sesiones activas de la misma mesa. También contiene
restricciones para valores no negativos o positivos, roles y estados
válidos. Los estados de `Sesion`, `Pedido` y `Cuenta` no se almacenan.

### Resultados comprobados

- Django conectó con la base local `sala_fogon`; se aplicó la migración
  `restaurant.0001_initial`. `manage.py check`, `migrate --check` y la
  comprobación de cambios pendientes de modelos terminaron correctamente.
- El endpoint `/api/health/` devolvió HTTP 200 y `database: ok` tanto
  directamente desde Django como a través del proxy de Vite. React compiló
  y Vite sirvió la página con HTTP 200.
- La estudiante creó `test_sala_fogon`, propiedad de `sala_fogon_app`.
  Django indicó que reutilizó esa base; las **13 pruebas estructurales**
  de `restaurant` pasaron y la base de pruebas se conservó. Entre ellas se
  verificaron la sesión activa única por mesa, otras unicidades, valores
  decimales, relaciones, valores inválidos y ausencia de columnas para
  estados derivados.

### Dificultades y comprobaciones pendientes

PostgreSQL exigía una contraseña local, que se introdujo sin compartirla
en el chat ni versionarla. El rol de la aplicación no tenía `CREATEDB`,
por lo que se creó una base de pruebas separada en pgAdmin. Vite falló
inicialmente con `EPERM` dentro del aislamiento de comandos y funcionó
al repetir la comprobación con acceso autorizado. Los comandos de los
servidores de desarrollo permanecieron abiertos por su naturaleza
persistente y generaron tarjetas de ejecución prolongada; las pruebas
posteriores del modelo se hicieron con comandos secuenciales que
terminan por sí solos.

Al cierre de esta primera etapa no se había automatizado una prueba de
la interfaz en navegador ni verificado la instalación desde cero en
otra máquina. Tampoco se habían probado aperturas simultáneas reales de
sesión ni reservas concurrentes de ingredientes. Los modelos de pedidos,
cocina y pagos existían, pero sus operaciones, transiciones, controles
de roles, reserva y devolución de ingredientes, y validaciones de cierre
y pago todavía estaban pendientes de implementación y prueba.

### Incrementos funcionales posteriores de la sesión 3

La estudiante autorizó por separado los incrementos de mesero, cocina y
cancelaciones, y cuentas con pagos parciales y cierre. Codex propuso e
implementó servicios transaccionales, endpoints con validación de rol y
una interfaz React sencilla. Para el primer flujo se decidió mantener el
pedido temporalmente en React y persistirlo solo al enviarlo a cocina;
el backend valida el consumo conjunto, descuenta ingredientes y registra
la composición histórica de cada unidad en una sola transacción. La
estudiante lo probó manualmente antes de publicar ese avance.

Para cocina, Codex propuso derivar la cola de los estados de los ítems,
permitir las transiciones independientes
`EN_COLA → EN_PREPARACION → LISTO` y devolver ingredientes históricos al
cancelar desde `EN_COLA`. Se añadieron bloqueos y pruebas con conexiones
PostgreSQL independientes para las carreras entre preparación y
cancelación y entre dos cancelaciones. La estudiante confirmó el flujo
manualmente y autorizó su publicación. La interfaz del mesero conserva
los pedidos completados y cancelados, muestra su número dentro de la
sesión y protege las consultas frente a respuestas antiguas.

En el incremento de cuentas, Codex propuso calcular consumo, pagos y
saldo desde los precios históricos de `ItemPedido` y las asignaciones,
sin guardar montos en `Cuenta` ni `Pago`; también propuso bloquear la
sesión y los ítems para registrar pagos o cerrar la atención. La
interfaz permite seleccionar unidades de pedidos distintos, ver un
importe calculado en centavos y registrar varios pagos parciales. El
backend calcula nuevamente los importes y rechaza selecciones vacías,
duplicadas, canceladas, ajenas a la sesión o ya pagadas. El cierre
comprueba que no queden unidades no canceladas sin pago y se coordina
con el envío de nuevos pedidos mediante el bloqueo de la sesión.

#### Duda y decisión sobre pagos y cancelaciones

Codex detectó que las reglas previas permitían cancelar un ítem
`EN_COLA`, pero no definían qué hacer si ese ítem ya estaba asignado a
un pago. Propuso impedir la cancelación de ítems pagados porque no existe
anulación de pagos. La estudiante aclaró su interpretación del
restaurante: los clientes primero piden, cocina termina la preparación
y después se registran los pagos. Decidió que **no se puede registrar
ningún pago mientras exista un ítem no cancelado `EN_COLA` o
`EN_PREPARACION` en la sesión**, aunque los ítems seleccionados ya estén
listos. Una vez que todos están `LISTO`, pueden registrarse pagos
parciales. Además, aprobó rechazar la cancelación de cualquier ítem que
ya tenga una asignación de pago, como protección adicional.

La primera versión del nuevo servicio de pagos solo exigía que los
ítems seleccionados no estuvieran cancelados; por tanto, habría
permitido pagar unidades en cola. Tras la aclaración de la estudiante,
Codex modificó el servicio para bloquear y revisar todos los ítems de
la sesión antes de crear el pago. La consulta de cuenta indica si el
pago está habilitado y React desactiva la selección mientras cocina
continúa. No se añadieron entidades, campos ni una condición distinta
para cerrar: el cierre sigue dependiendo de que todo el consumo no
cancelado esté pagado.

#### Verificaciones y dificultades de los incrementos

- La suite completa terminó con **56 pruebas Django aprobadas**, usando
  exclusivamente `test_sala_fogon` con `--keepdb`. Incluye las pruebas
  previas y las nuevas de cuentas, precios históricos, pagos parciales,
  reversión ante fallos, cierre y carreras. Las pruebas de concurrencia
  emplean conexiones y procesos PostgreSQL independientes y comprueban
  también el estado final de pagos, ítems e ingredientes; no miden el
  rendimiento ni demuestran ausencia de toda carrera posible.
- Pasaron **4 pruebas JavaScript** del descarte de respuestas antiguas y
  del cálculo de importes en centavos. `manage.py check` no reportó
  errores; `makemigrations --check --dry-run` no detectó cambios y
  `migrate --check` no encontró migraciones pendientes. La compilación
  de React con `npm run build` terminó correctamente.
- En una ejecución intermedia falló una prueba nueva porque comparaba
  identificadores devueltos por una consulta sin orden explícito; se
  corrigió el test con `order_by("id")` y pasó la suite completa. El
  runner de Node y Vite encontraron `EPERM` al crear procesos hijos
  dentro del aislamiento de comandos; las verificaciones pasaron al
  ejecutarlas con acceso autorizado fuera de ese aislamiento. No se
  iniciaron servidores persistentes para esas comprobaciones.
- La estudiante realizó las pruebas manuales del nuevo flujo de cuenta,
  pagos parciales y cierre en el navegador y confirmó que el
  funcionamiento observado es correcto. También había probado
  manualmente los incrementos anteriores.

Siguen pendientes una prueba automatizada de la interfaz en navegador,
la instalación desde cero en otra máquina y pruebas específicas de dos
aperturas simultáneas de la misma mesa y de dos envíos simultáneos de
pedidos. Los apartados «Actualización de la sesión 3» de los ADR
describen el hito inicial de modelo y entorno; estos incrementos
posteriores no cambiaron las decisiones arquitectónicas aceptadas.
Tras la prueba manual, la estudiante solicitó retirar el rótulo visual
«Unidad» y su identificador en React. Codex quitó esos identificadores
de las filas de mesero, cocina y cuenta, y de los mensajes visibles;
los IDs permanecen en la API y como claves internas para conservar las
operaciones independientes. Las cuatro pruebas JavaScript y la
compilación de React volvieron a pasar tras el ajuste. Este cambio de
presentación no modificó el modelo relacional ni las reglas de negocio.
