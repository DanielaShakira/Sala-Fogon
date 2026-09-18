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

La división de una cuenta se representará mediante grupos visuales de pago, por ejemplo "Comensal 1", "Comensal 2", etc., pero estos grupos no representan un registro real de la cantidad de personas presentes.

**Motivo:** la división de la cuenta sí es necesaria, pero conocer el número real de comensales no aporta una funcionalidad requerida por el problema.

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
