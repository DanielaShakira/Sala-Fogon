## Propósito

Este documento registra las decisiones asumidas para resolver aspectos del problema que no se encuentran completamente especificados en el enunciado.

Las suposiciones podrán modificarse durante el desarrollo si una decisión posterior demuestra que existe una alternativa más adecuada para cumplir las reglas de negocio.

---

## A-001 — Una mesa puede tener varias órdenes durante una misma sesión

Se asume que una mesa puede generar varias órdenes mientras permanece abierta.

Por ejemplo, una mesa puede realizar una primera orden, recibirla y posteriormente realizar una segunda orden.

Por esta razón, los pedidos no se relacionarán directamente con la mesa, sino mediante una sesión de atención.

**Motivo:** permite representar de manera natural varias órdenes realizadas durante la permanencia de una mesa en el restaurante.

---

## A-002 — La sesión representa la atención de una mesa

Se asume que una mesa tiene una sesión mientras está siendo atendida.

La sesión comienza cuando se inicia la atención de la mesa y finaliza cuando se cierra su cuenta.

Una sesión puede contener múltiples pedidos.

**Motivo:** permite agrupar el consumo completo de una mesa, incluso cuando existen varios pedidos.

---

## A-003 — No se almacenará el número de comensales

El sistema no necesita registrar cuántas personas están sentadas en una mesa.

La división de la cuenta se representará mediante diferentes pagos, por ejemplo "Pago 1", "Pago 2", etc., sin crear una entidad que represente a cada comensal.

**Motivo:** la división de la cuenta sí es necesaria, pero conocer o registrar el número de comensales no aporta una funcionalidad requerida por el problema.

---

## A-004 — Los ingredientes se manejarán mediante porciones abstractas

Se asumirá que cada ingrediente posee una cantidad disponible expresada mediante una unidad abstracta de consumo definida por el restaurante.

Una porción no representa necesariamente una medida física única. Dependiendo del ingrediente, puede corresponder a kilogramos, mililitros, tazas, unidades u otra forma de cuantificación utilizada por el restaurante.

**Motivo:** permite controlar la disponibilidad necesaria para decidir si un plato puede solicitarse sin convertir el sistema en un sistema completo de inventario.

---

## A-005 — La disponibilidad de ingredientes afecta la disponibilidad de los platos

Un plato solamente podrá ser solicitado cuando el plato esté activo y los ingredientes requeridos se encuentren activos y disponibles en cantidad suficiente.

La disponibilidad del plato será calculada a partir de su composición actual y de las cantidades disponibles de sus ingredientes.

No se almacenará un campo disponible en Plato.

**Motivo:** responde directamente a la regla del enunciado que establece que un plato sin ingredientes disponibles no puede ser solicitado y debe dejar de ofrecerse.

---

## A-006 — La complejidad representa carga de preparación

Cada preparación podrá tener un puntaje interno de carga de preparación.

Este valor no pretende representar una medida objetiva de dificultad culinaria, sino una referencia utilizada por el sistema para estimar la carga asociada a un pedido.

El sistema podrá utilizar la suma de estos valores para generar una recomendación sobre la cantidad de cocineros que podría requerir el pedido.

**Importante:** el sistema no asignará físicamente cocineros a los pedidos.

**Motivo:** se desea representar la carga de trabajo sin convertir la aplicación en un sistema de asignación de personal.

---

## A-007 — La preparación de los ítems puede ocurrir de manera simultánea

Se asumirá que los diferentes ítems de los pedidos pueden prepararse simultáneamente.

El ordenamiento de la cola de cocina indica la antigüedad de los pedidos pendientes, pero no implica que un pedido deba terminar completamente antes de comenzar otro.

**Motivo:** el enunciado establece estados independientes para los ítems y requiere una cola ordenada por antigüedad con los pendientes agrupados.

---

## A-008 — La cuenta corresponde a la sesión de la mesa

Al cerrar la atención de una mesa, la cuenta incluirá el consumo de los diferentes pedidos realizados durante la sesión.

La cuenta podrá dividirse en diferentes pagos.

Cada unidad solicitada se representa mediante un ÍtemPedido independiente, por lo que diferentes unidades de un mismo plato pueden asociarse a diferentes pagos.

**Motivo:** permite cumplir la regla de dividir la cuenta entre varios pagos parciales sin necesidad de registrar un número real de comensales.

---

## A-009 — Los pagos serán registrados, no procesados electrónicamente

El sistema permitirá registrar pagos parciales y controlar qué unidades del consumo han sido asignadas a un pago.

No se implementará una pasarela de pagos ni procesamiento real de dinero mediante servicios externos.

**Motivo:** el registro de pagos es necesario para representar la división de la cuenta, mientras que los pagos reales se encuentran fuera del alcance de la prueba.

---

## A-010 — Un ítem puede cancelarse antes de iniciar su preparación

Un ÍtemPedido podrá cancelarse solamente cuando su estado sea `EN_COLA.`

La cancelación no forma parte del flujo normal de preparación. El flujo normal de un ítem es:

`EN_COLA → EN_PREPARACION → LISTO`

Una vez que el ítem entra en `EN_PREPARACION`, ya no puede ser cancelado.

**Motivo:** permite representar la regla del enunciado que establece que un ítem solo puede cancelarse si la cocina todavía no ha comenzado su preparación.

---

## A-011 — Los ítems cancelados permanecen registrados pero no participan en la operación activa

Los ítems cancelados no serán eliminados físicamente de la base de datos.

Permanecerán registrados con estado `CANCELADO`, pero no participarán en la preparación pendiente ni en el cálculo de la cuenta.

Si el ítem había reservado ingredientes, estos podrán ser devueltos a la disponibilidad al momento de la cancelación.

**Motivo:** conservar el registro del pedido permite mantener trazabilidad sin considerar como consumo una unidad que fue cancelada.

---

## A-012 — El estado del pedido considera únicamente los ítems no cancelados

No se almacenará físicamente un campo estado en Pedido.

El estado operativo del pedido se calculará a partir de los estados de sus ÍtemPedido, ignorando los ítems cancelados para determinar el avance de preparación.

Si todos los ítems fueron cancelados, el pedido se considera cancelado.

Si existen ítems no cancelados, el estado se determina según su avance de preparación.

**Motivo:** evita duplicar información y permite que los estados individuales de los ítems sean la única fuente de verdad sobre la preparación.

---

## A-013 — Las observaciones se registrarán a nivel de pedido

Las observaciones se almacenarán en `Pedido` y no en cada `ÍtemPedido`.

No se implementará inicialmente un campo de observaciones específico para cada plato solicitado.

**Motivo:** mantener el alcance controlado y evitar añadir complejidad al modelo para una funcionalidad que no es requerida explícitamente por el enunciado.

---

## A-014 — Los usuarios tendrán roles operativos básicos

El sistema contará con usuarios asociados a un rol operativo.

Los roles considerados serán:

- `ADMIN`
- `MESERO`
- `COCINERO`

El usuario `ADMIN` podrá gestionar la configuración de platos e ingredientes; el `MESERO` gestionará las sesiones y pedidos; el `COCINERO` gestionará el avance de preparación de los ítems.

No se implementará un sistema avanzado de autenticación.

**Motivo:** es necesario distinguir las responsabilidades de los actores principales del restaurante, pero la autenticación avanzada se encuentra fuera del alcance de la prueba.

---

## A-015 — Se conservará la composición de ingredientes utilizada por cada ítem pedido

Cuando un pedido sea enviado a cocina, se registrará en `ComposiciónItemPedido` la composición de ingredientes correspondiente a
cada unidad solicitada.

Esta información no se actualizará si posteriormente cambia la receta actual del plato.

**Motivo:** permite saber qué ingredientes fueron realmente comprometidos para un pedido concreto y facilita devolver las cantidades reservadas si un ítem se cancela.

---

## A-016 — Una sesión solo puede cerrarse cuando su cuenta está completamente pagada

La sesión no podrá cerrarse mientras existan unidades no canceladas de la cuenta que no hayan sido asignadas a un pago.

La condición será validada mediante la lógica de negocio.

**Motivo:** evita cerrar una atención dejando consumo pendiente de pago.

---

## A-017 --- Cada unidad solicitada se representa como un ÍtemPedido independiente

Si un cliente solicita varias unidades del mismo plato, cada unidad se almacenará como un registro independiente de `ÍtemPedido`.

Por ejemplo, tres hamburguesas se representan mediante tres ítems distintos, en lugar de un solo ítem con `cantidad = 3`.

La interfaz podrá agrupar visualmente unidades iguales para facilitar el trabajo de cocina.

**Motivo:** permite que cada unidad avance de forma independiente por los estados de preparación y facilita su asignación individual a diferentes pagos.

---

## A-018 --- La cantidad requerida de ingredientes es una unidad abstracta de consumo

`ComposiciónPlato.cantidad_requerida` representa la cantidad abstracta de ingrediente que requiere una unidad del plato.

La unidad física concreta no será modelada por el sistema.

Por ejemplo, si el restaurante define que una preparación consume dos porciones de un ingrediente, se registrará `2`, independientemente de si para ese ingrediente una porción corresponde a gramos, mililitros, tazas, unidades u otra medida definida por el restaurante.

**Motivo:** permite modelar el consumo de ingredientes sin construir un sistema completo de unidades de medida e inventario.

---

## A-019 --- La disponibilidad de ingredientes se reserva al enviar el pedido a cocina

Mientras el mesero está construyendo un pedido, los ingredientes no se descuentan.

Al enviar el pedido a cocina, el sistema:

1. valida nuevamente la disponibilidad de los ingredientes;
2. registra la composición de cada `ÍtemPedido`;
3. descuenta las cantidades correspondientes de `Ingrediente`;
4. coloca los ítems en `EN_COLA`.

Si un pedido en cola se modifica para agregar o retirar unidades, se aplicarán nuevamente las validaciones y ajustes correspondientes.

**Motivo:** evita que dos operaciones basadas en información desactualizada comprometan las mismas existencias y permite representar la reserva de ingredientes sin crear una entidad adicional de inventario reservado.

---

## A-020 --- Los estados derivados no se almacenarán como datos independientes

No se almacenarán físicamente los estados de `Pedido` ni de `Cuenta`.

El estado de `Pedido` se deriva de los estados de sus ítems.

El estado de `Cuenta` se deriva de la asignación de los ítems no cancelados a los pagos.

En `Sesión` tampoco se almacenará un campo `estado`: una sesión se considera activa cuando `fecha_hora_fin` es `NULL` y cerrada cuando posee una fecha de finalización.

**Motivo:** evitar duplicación de información y reducir la posibilidad de inconsistencias entre datos almacenados y datos derivados.
