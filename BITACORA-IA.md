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

## Sesión 2 — Revisión y consolidación del modelo de datos

### Objetivo

Revisar las decisiones tomadas durante la sesión anterior y convertirlas en un modelo de datos coherente antes de comenzar la implementación.

La sesión también buscó identificar decisiones que todavía podían generar inconsistencias entre los estados de los pedidos, la preparación en cocina, la disponibilidad de ingredientes y la cuenta.

### Uso de IA

Se utilizó ChatGPT como herramienta de apoyo para:

* Revisar las entidades y atributos definidos durante la sesión anterior.

* Detectar decisiones pendientes o posibles contradicciones en el modelo.

* Analizar el comportamiento de los pedidos cuando existen ítems cancelados.

* Analizar cómo conservar la consistencia histórica cuando cambia la composición de un plato.

* Revisar la relación entre usuarios, sesiones, pedidos, cocina y cuenta.

* Comprobar que las entidades propuestas fueran suficientes para cubrir las reglas del enunciado sin ampliar innecesariamente el alcance.

### Proceso de decisión

Durante la revisión se identificaron dos decisiones que requerían una definición explícita.

La primera correspondía a la cancelación de ítems. Se estableció que `CANCELADO` no forma parte del flujo normal de preparación, sino que representa una situación excepcional que solamente puede ocurrir mientras el ítem permanece en `EN_COLA`.

La segunda correspondía a los cambios posteriores en la receta de un plato. Se consideró que utilizar siempre la composición actual podría modificar la interpretación histórica de pedidos ya realizados.

A partir de esto se decidió conservar, junto al ítem pedido, la composición de ingredientes utilizada en el momento en que el pedido fue enviado a cocina.

### Decisiones tomadas

La estudiante decidió:

1. Incorporar `CANCELADO` como estado excepcional de `ÍtemPedido`.

2. Permitir la cancelación únicamente mientras el ítem se encuentre `EN_COLA`.

3. Mantener los ítems cancelados registrados, pero excluirlos de la preparación, del estado operativo del pedido y del cálculo de la cuenta.

4. Considerar un pedido como `CANCELADO` cuando todos sus ítems estén cancelados.

5. Determinar el estado operativo de un pedido considerando únicamente sus ítems no cancelados.

6. Mantener las observaciones a nivel general del pedido en lugar de crear observaciones independientes por ítem.

7. Incorporar una entidad `Usuario` con roles básicos de `ADMIN`, `MESERO` y `COCINERO`, sin implementar autenticación avanzada.

8. Asociar el mesero responsable a la sesión de la mesa.

9. Conservar una copia de la composición de ingredientes utilizada por cada ítem cuando este sea enviado a cocina.

10. Permitir cerrar una sesión únicamente cuando su cuenta esté completamente pagada.

### Modelo conceptual resultante

Como resultado de la revisión, las entidades principales consideradas para el sistema son:

* `Mesa`

* `Usuario`

* `Sesion`

* `Pedido`

* `ItemPedido`

* `Plato`

* `Ingrediente`

* `ComposicionPlato`

* `ComposicionItemPedido`

* `Cuenta`

* `Pago`

* `AsignacionPago`

Las entidades serán revisadas nuevamente al momento de convertir el modelo conceptual en el modelo relacional y en las estructuras concretas de implementación.

### Reflexión

La revisión permitió comprobar que algunas decisiones que inicialmente parecían pequeños detalles podían afectar varias reglas del sistema.

En particular, la cancelación de un ítem debía conservarse como información histórica sin afectar la preparación ni el cobro, mientras que los cambios de una receta no debían modificar retrospectivamente pedidos que ya habían sido realizados.

También se confirmó la intención de mantener el alcance reducido: el modelo busca resolver las reglas planteadas por el problema sin convertirse en un sistema completo de administración de restaurantes.

### Pendiente para la siguiente sesión

* Convertir el modelo conceptual en un modelo relacional.

* Definir claves primarias, claves foráneas y restricciones.

* Definir la tecnología de implementación.

* Preparar la estructura inicial del proyecto antes de comenzar el desarrollo funcional.