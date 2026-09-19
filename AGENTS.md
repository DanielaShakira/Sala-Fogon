# AGENTS.md

## Propósito del proyecto

Este repositorio contiene el desarrollo del sistema de gestión de pedidos y cocina para un restaurante, realizado como parte de la prueba técnica individual de Herramientas de Empleabilidad en Ingeniería de Sistemas.

El sistema busca mejorar la comunicación entre el personal de servicio y la cocina, permitiendo gestionar pedidos, controlar su preparación por ítem, consultar la cola de cocina y gestionar el pago de la cuenta de una mesa.

El proyecto debe resolver las reglas de negocio indicadas en el enunciado y mantenerse dentro del alcance definido para la prueba.

---

## Contexto funcional

El restaurante trabaja con mesas atendidas por meseros.

Una mesa puede tener una sesión de atención activa. Durante una sesión pueden existir varios pedidos.

Cada pedido contiene uno o varios ítems y cada ítem corresponde a un plato solicitado.

Los ítems de un pedido tienen estados de preparación independientes.

El flujo normal de un ítem es:

`EN_COLA → EN_PREPARACION → LISTO`

Un ítem puede pasar excepcionalmente a `CANCELADO` mientras se encuentre en `EN_COLA`.

Los ítems cancelados permanecen registrados, pero no participan en la preparación, en el estado operativo del pedido ni en el cálculo de la cuenta.

El pedido se considera cancelado cuando todos sus ítems están cancelados.

---

## Entidades principales

El modelo conceptual definido hasta el momento contempla:

- `Mesa`
- `Usuario`
- `Sesion`
- `Pedido`
- `ItemPedido`
- `Plato`
- `Ingrediente`
- `ComposicionPlato`
- `ComposicionItemPedido`
- `Cuenta`
- `Pago`
- `AsignacionPago`

### Relaciones principales

- Una `Mesa` puede tener múltiples `Sesion` a lo largo del tiempo.
- Una `Sesion` pertenece a una `Mesa`.
- Una `Sesion` tiene un `Usuario` con rol de `MESERO`.
- Una `Sesion` puede contener múltiples `Pedido`.
- Un `Pedido` contiene múltiples `ItemPedido`.
- Un `ItemPedido` referencia un `Plato`.
- Un `Plato` está compuesto por múltiples `Ingrediente` mediante `ComposicionPlato`.
- `ComposicionPlato` registra la cantidad requerida de cada ingrediente.
- Un `ItemPedido` conserva la composición de ingredientes utilizada para ese pedido mediante `ComposicionItemPedido`.
- Una `Sesion` tiene una `Cuenta`.
- Una `Cuenta` puede tener múltiples `Pago`.
- Un `Pago` contiene múltiples `AsignacionPago`.
- Una `AsignacionPago` indica qué cantidad de un `ItemPedido` pertenece a un pago.

---

## Reglas de negocio ya decididas

### Pedidos

- Una mesa puede generar varios pedidos durante una misma sesión.
- Un pedido tiene observaciones generales.
- Cada ítem mantiene su propio estado de preparación.
- Un pedido solo se considera listo cuando todos sus ítems no cancelados están listos.
- Si todos los ítems de un pedido están cancelados, el pedido queda cancelado.
- Los ítems cancelados no cuentan para el estado operativo ni para la cuenta.

### Cancelación

- Un ítem solamente puede cancelarse cuando está `EN_COLA`.
- Un ítem que ya está `EN_PREPARACION` no puede cancelarse.
- La cancelación debe conservarse como información histórica.

### Platos e ingredientes

- Un plato debe dejar de ofrecerse cuando no cuenta con los ingredientes requeridos.
- La disponibilidad del plato se determina a partir de la disponibilidad de sus ingredientes y de su estado de activación.
- Los ingredientes se manejan mediante cantidades abstractas de porciones o unidades de consumo.
- No se implementará un sistema completo de inventario.
- Cuando un pedido entra a `EN_COLA`, se valida la disponibilidad y se reservan las cantidades necesarias reduciendo `cantidad_disponible`.
- Si un pedido se modifica mientras está en cola, las cantidades de ingredientes deben volver a validarse.
- Las modificaciones que liberen cantidades reservadas deben restaurar dichas cantidades.

### Historial de recetas

La composición actual de un `Plato` representa su receta vigente.

Cuando un `ItemPedido` es enviado a cocina, debe conservarse la composición de ingredientes utilizada en ese momento mediante `ComposicionItemPedido`.

Los cambios posteriores en la receta no deben modificar retrospectivamente los pedidos ya realizados.

### Precios

`Plato.precio` representa el precio actual del plato.

`ItemPedido.precio_unitario` conserva el precio aplicado al momento de realizar el pedido.

Los cambios posteriores de precio no deben modificar el valor histórico de los pedidos existentes.

### Usuarios

Los roles operativos considerados son:

- `ADMIN`
- `MESERO`
- `COCINERO`

El `MESERO` puede consultar platos disponibles y enviar pedidos a cocina.

El `COCINERO` puede consultar la cola y actualizar los estados de preparación.

El `ADMIN` puede realizar las configuraciones necesarias de platos e ingredientes.

No se implementará autenticación avanzada.

### Cuenta y pagos

- La cuenta pertenece a la sesión, no a un pedido individual.
- Una sesión puede contener múltiples pedidos que forman parte de la misma cuenta.
- Una cuenta puede dividirse entre múltiples pagos.
- Un mismo `ItemPedido` puede distribuirse entre diferentes pagos cuando su cantidad sea mayor que uno.
- Un pago puede contener ítems provenientes de diferentes pedidos.
- El monto de un pago se calcula a partir de las asignaciones de ítems; no se registra manualmente un monto.
- Los ítems cancelados no participan en el valor de la cuenta.
- Una sesión solamente puede cerrarse cuando su cuenta está completamente pagada.

---

## Cola de cocina

La consulta obligatoria del sistema debe mostrar la cola de cocina ordenada por antigüedad y con los ítems pendientes agrupados por pedido.

La antigüedad se determina mediante la fecha y hora de creación del pedido.

El orden de la cola no implica que los pedidos deban prepararse completamente de forma secuencial. Los ítems pueden prepararse simultáneamente.

---

## Carga de preparación

Cada `Plato` posee un puntaje de carga de preparación.

El puntaje representa una estimación interna de la carga asociada a preparar el plato.

El sistema puede utilizar estos valores para calcular una recomendación sobre la cantidad de cocineros necesaria.

El sistema no asignará físicamente cocineros a pedidos.

---

## Alcance

El sistema debe priorizar:

- Persistencia de datos.
- Interfaz para operar el sistema.
- Reglas de negocio del enunciado.
- Consulta de la cola de cocina.
- Gestión de pedidos.
- Gestión de estados de preparación.
- Disponibilidad de platos según ingredientes.
- Gestión de cuenta y pagos parciales.

Quedan fuera de alcance:

- Autenticación avanzada.
- Pagos reales o pasarelas de pago.
- Despliegue en producción.
- Integraciones externas.
- Sistema completo de inventario.
- Asignación automática de cocineros.
- Funcionalidades no necesarias para resolver el problema de la prueba.

---

## Forma de trabajo con agentes de IA

La IA se utilizará como herramienta de apoyo, no como autoridad para tomar decisiones de diseño.

Antes de modificar decisiones arquitectónicas importantes, el agente debe:

1. Identificar qué decisión existente se vería afectada.
2. Explicar la alternativa propuesta.
3. Compararla con la decisión actual.
4. Indicar las consecuencias.
5. Esperar la decisión de la estudiante cuando la modificación tenga impacto relevante.

No se deben introducir entidades, funcionalidades o dependencias únicamente porque sean habituales en sistemas similares.

El agente debe respetar las decisiones documentadas en:

- `ASSUMPTIONS.md`
- `ADR/`
- `BITACORA-IA.md`

Si una implementación requiere modificar una decisión previamente documentada, debe señalarlo antes de realizar el cambio.

---

## Principios de desarrollo

- Priorizar las reglas de negocio sobre funcionalidades accesorias.
- Mantener el alcance limitado a la prueba.
- Preferir soluciones simples y comprensibles.
- Evitar sobreingeniería.
- Mantener separadas las responsabilidades del sistema.
- Las reglas de negocio importantes deben estar reflejadas en el código y ser verificables.
- El código generado mediante IA debe ser revisado y comprendido antes de incorporarse.
- No ocultar decisiones importantes dentro de código generado automáticamente.
- Mantener nombres consistentes con el modelo conceptual y la documentación.

---

## Documentación

Los principales documentos del proyecto son:

- `README.md`: descripción, instalación, ejecución y funcionamiento.
- `AGENTS.md`: contexto, reglas de trabajo y decisiones funcionales relevantes para agentes de IA.
- `ASSUMPTIONS.md`: supuestos adoptados para completar aspectos no especificados del problema.
- `BITACORA-IA.md`: registro del uso de IA durante el desarrollo.
- `ADR/`: decisiones importantes de arquitectura y diseño.

Los documentos deben actualizarse cuando una decisión relevante cambie durante el desarrollo.

---

## Estado actual del proyecto

El análisis funcional y el modelo conceptual inicial ya fueron definidos.

La siguiente etapa consiste en:

1. Convertir el modelo conceptual en un modelo relacional.
2. Definir claves primarias, claves foráneas y restricciones.
3. Elegir la tecnología de implementación.
4. Crear la estructura inicial del proyecto.
5. Implementar progresivamente las reglas de negocio.
6. Registrar en `BITACORA-IA.md` las decisiones tomadas durante la implementación.

No asumir que una decisión técnica pendiente ya fue tomada. Si una decisión depende de la tecnología elegida, debe analizarse cuando se seleccione dicha tecnología.