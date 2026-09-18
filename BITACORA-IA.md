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
