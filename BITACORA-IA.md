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
