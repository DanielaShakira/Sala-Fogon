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

La división de una cuenta se representará mediante diferentes pagos, sin crear registros que representen a los comensales.

**Motivo:** la división de la cuenta sí es necesaria, pero conocer o registrar el número de comensales no aporta una funcionalidad requerida por el problema.

---

## A-004 — Los ingredientes se manejarán mediante porciones abstractas

Se asumirá que cada ingrediente posee una cantidad disponible expresada en porciones o unidades de consumo, sin especificar medidas físicas como gramos, mililitros o litros.

Por ejemplo, una preparación puede requerir 2 porciones de carne.

**Motivo:** permite controlar la disponibilidad necesaria para decidir si un plato puede solicitarse sin convertir el sistema en un sistema completo de inventario.

---

## A-005 — La disponibilidad de ingredientes afecta la disponibilidad de los platos

Un plato solamente podrá ser solicitado cuando los ingredientes requeridos se encuentren disponibles.

La disponibilidad podrá depender de la cantidad de porciones disponibles y de una posible desactivación manual del ingrediente.

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

Un mismo ítem podrá distribuirse entre diferentes pagos cuando tenga una cantidad mayor a uno.

**Ejemplo:** si un pedido contiene 3 hamburguesas iguales, una podrá asociarse a un pago y las otras dos a otro.

**Motivo:** permite cumplir la regla de dividir la cuenta entre varios pagos parciales sin necesidad de registrar un número real de comensales.

---

## A-009 — Los pagos serán registrados, no procesados electrónicamente

El sistema permitirá registrar pagos parciales y controlar cuánto queda pendiente de la cuenta.

No se implementará una pasarela de pagos ni procesamiento real de dinero mediante servicios externos.

**Motivo:** el registro de pagos es necesario para representar la división de la cuenta, mientras que los pagos reales se encuentran fuera del alcance de la prueba.

---

## A-010 — Un ítem puede cancelarse antes de iniciar su preparación

Se asume que un ítem de pedido puede pasar excepcionalmente al estado `CANCELADO` mientras se encuentre en `EN_COLA`.

La cancelación no forma parte del flujo normal de preparación. El flujo normal de un ítem es:

`EN_COLA → EN_PREPARACION → LISTO`

Una vez que el ítem entra en `EN_PREPARACION`, ya no puede ser cancelado.

**Motivo:** permite representar la regla del enunciado que establece que un ítem solo puede cancelarse si la cocina todavía no ha comenzado su preparación.

---

## A-011 — Los ítems cancelados permanecen registrados pero no participan en la operación activa

Un ítem cancelado se conservará en el sistema como parte del historial del pedido, pero no se tendrá en cuenta para determinar qué debe preparar la cocina, el estado operativo del pedido ni el valor de la cuenta.

**Motivo:** conservar el registro de la cancelación permite mantener trazabilidad sin que un ítem que ya no debe prepararse afecte las operaciones posteriores.

---

## A-012 — El estado del pedido considera únicamente los ítems no cancelados

El estado de un pedido se determinará considerando únicamente los ítems que no se encuentren cancelados.

Si existen ítems activos en diferentes estados, el estado del pedido representará el estado general de preparación de dichos ítems.

Cuando todos los ítems del pedido estén cancelados, el pedido pasará a `CANCELADO`.

**Motivo:** evita que un ítem cancelado impida que el resto del pedido avance normalmente y permite representar el caso en que un pedido deja de tener preparaciones pendientes.

---

## A-013 — Las observaciones se registrarán a nivel de pedido

Las observaciones se almacenarán en el pedido como una indicación general para la cocina.

No se registrarán observaciones independientes para cada ítem.

Se asume que el restaurante establecerá un lenguaje operativo claro entre meseros y cocina para comunicar indicaciones específicas cuando sea necesario.

**Motivo:** mantener las observaciones a nivel de pedido reduce la complejidad del sistema y resulta suficiente para el alcance de la prueba.

---

## A-014 — Los usuarios tendrán roles operativos básicos

El sistema contará con usuarios asociados a un rol operativo.

Los roles considerados serán:

- `ADMIN`
- `MESERO`
- `COCINERO`

El mesero podrá consultar los platos disponibles y enviar pedidos a cocina.

El cocinero podrá consultar y actualizar el estado de preparación de los ítems.

El administrador podrá realizar las operaciones de configuración necesarias para platos e ingredientes.

No se implementará un sistema avanzado de autenticación.

**Motivo:** es necesario distinguir las responsabilidades de los actores principales del restaurante, pero la autenticación avanzada se encuentra fuera del alcance de la prueba.

---

## A-015 — Se conservará la composición de ingredientes utilizada por cada ítem pedido

La composición actual de un plato representa su receta vigente. Sin embargo, cuando un ítem de pedido sea enviado a cocina, se conservará la composición de ingredientes que fue utilizada para ese pedido.

Por ejemplo, si una hamburguesa requería inicialmente 2 porciones de carne y posteriormente su receta cambia a 1 porción, un pedido realizado antes del cambio conservará la composición utilizada originalmente.

**Motivo:** permite mantener consistencia histórica y evita que modificaciones posteriores en la receta alteren la interpretación de pedidos ya realizados.

---

## A-016 — Una sesión solo puede cerrarse cuando su cuenta está completamente pagada

Una sesión permanecerá activa mientras su cuenta tenga valores pendientes de pago.

La sesión podrá pasar a `CERRADA` únicamente cuando todas las cantidades de los ítems que deben cobrarse hayan sido completamente asignadas a pagos y la cuenta se encuentre `PAGADA`.

**Motivo:** evita cerrar una atención que todavía posee consumo pendiente de pago.