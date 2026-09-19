# AGENTS.md

## Propósito del proyecto

Este repositorio contiene el desarrollo del sistema de gestión de
pedidos y cocina para un restaurante, realizado como parte de la prueba
técnica individual de Herramientas de Empleabilidad en Ingeniería de
Sistemas.

El sistema busca mejorar la comunicación entre el personal de servicio y
la cocina, especialmente en el seguimiento de los pedidos y sus estados
de preparación.

## Forma de trabajo

El desarrollo se realizará de manera incremental durante múltiples días
previos a la entrega.

Las decisiones relevantes de diseño deberán quedar documentadas mediante
ADR (Architecture Decision Record) cuando impliquen una elección entre
alternativas o tengan impacto sobre la estructura o funcionamiento del
sistema.

Las suposiciones necesarias debido a la información incompleta del
enunciado deberán registrarse en `ASSUMPTIONS.md`.

El uso de herramientas de inteligencia artificial deberá registrarse en
`BITACORA-IA.md`, indicando qué se solicitó, qué propuesta fue obtenida
y qué decisiones fueron tomadas finalmente por la estudiante.

La forma de trabajo esperada es:

1.  La estudiante plantea una necesidad, interpretación o alternativa.
2.  La IA ayuda a cuestionar, comparar y explorar consecuencias.
3.  Se revisan alternativas y casos límite.
4.  La estudiante toma la decisión final.
5.  La decisión adoptada se refleja en el código y, cuando corresponda,
    en la documentación.

La IA no debe convertir automáticamente una sugerencia en un requisito.
Las decisiones deben mantenerse trazables y ser comprendidas por la
estudiante antes de incorporarse al proyecto.

## Contexto funcional actual

El sistema representa la operación de pedidos y cocina de un
restaurante.

El flujo principal previsto es:

1.  Un mesero inicia una sesión para una mesa.
2.  La sesión puede contener múltiples pedidos.
3.  El mesero crea un pedido seleccionando platos disponibles.
4.  Cada unidad solicitada se representa como un `ÍtemPedido`
    independiente.
5.  Al enviar el pedido a cocina, se vuelve a validar la disponibilidad
    de ingredientes.
6.  Para cada ítem se registra la composición de ingredientes
    comprometida y se descuentan las cantidades disponibles.
7.  Los ítems ingresan a `EN_COLA`.
8.  Cocina puede avanzar cada ítem de forma independiente a
    `EN_PREPARACION` y posteriormente a `LISTO`.
9.  Un ítem solo puede cancelarse mientras esté `EN_COLA`.
10. El pedido se considera completo cuando todos sus ítems no cancelados
    están listos.
11. La cuenta pertenece a la sesión y reúne el consumo de todos sus
    pedidos.
12. La cuenta puede dividirse mediante varios pagos, asignando unidades
    individuales de los pedidos a cada pago.
13. La sesión solamente puede cerrarse cuando todo el consumo no
    cancelado ha sido asignado a pagos.

## Modelo conceptual y relacional actual

Las entidades principales son:

-   `Usuario`
-   `Mesa`
-   `Sesion`
-   `Pedido`
-   `ItemPedido`
-   `Plato`
-   `Ingrediente`
-   `ComposicionPlato`
-   `ComposicionItemPedido`
-   `Cuenta`
-   `Pago`
-   `AsignacionPago`

### Usuario

``` text
Usuario
- id
- nombre
- rol
- activo
```

Roles previstos:

-   `ADMIN`
-   `MESERO`
-   `COCINERO`

No se implementará autenticación avanzada.

### Mesa

``` text
Mesa
- id
- numero
```

La ocupación de una mesa se determina mediante sus sesiones. No se
almacena un estado independiente de ocupación.

### Sesión

``` text
Sesion
- id
- fecha_hora_inicio
- fecha_hora_fin
- mesa_id FK → Mesa.id
- mesero_id FK → Usuario.id
```

Una mesa puede tener muchas sesiones a lo largo del tiempo.

Una sesión pertenece a una mesa y registra el mesero responsable de la
atención.

No se almacena `estado`: si `fecha_hora_fin` es `NULL`, la sesión está
activa; si tiene valor, está cerrada.

La base de datos deberá impedir, cuando la tecnología escogida lo
permita mediante una restricción apropiada, que una mesa tenga más de
una sesión activa simultáneamente.

### Pedido

``` text
Pedido
- id
- fecha_hora_creacion
- observaciones
- sesion_id FK → Sesion.id
```

Una sesión puede contener múltiples pedidos.

No se almacena `estado`. El estado operativo se deriva de los estados de
sus ítems.

### ÍtemPedido

``` text
ItemPedido
- id
- precio_unitario
- estado
- pedido_id FK → Pedido.id
- plato_id FK → Plato.id
```

Cada unidad solicitada es un `ItemPedido` independiente.

Estados:

-   `EN_COLA`
-   `EN_PREPARACION`
-   `LISTO`
-   `CANCELADO`

Flujo normal:

``` text
EN_COLA → EN_PREPARACION → LISTO
```

Cancelación:

``` text
EN_COLA → CANCELADO
```

El precio se copia desde `Plato.precio` al momento de crear el ítem para
conservar el precio aplicado al pedido aunque el precio actual del plato
cambie posteriormente.

### Plato

``` text
Plato
- id
- nombre
- precio
- puntaje_carga_preparacion
- activo
```

No se almacena `disponible`.

Un plato puede solicitarse cuando está activo y todos los ingredientes
requeridos están activos y disponibles en cantidad suficiente.

### Ingrediente

``` text
Ingrediente
- id
- nombre
- cantidad_disponible
- activo
```

La cantidad se maneja mediante una unidad abstracta de consumo definida
por el restaurante.

No se implementará un sistema completo de inventario.

### ComposiciónPlato

``` text
ComposicionPlato
- id
- plato_id FK → Plato.id
- ingrediente_id FK → Ingrediente.id
- cantidad_requerida
```

Representa la receta o composición actual del plato.

Debe existir una restricción de unicidad sobre:

``` text
(plato_id, ingrediente_id)
```

para impedir que el mismo ingrediente aparezca duplicado en la
composición de un plato.

### ComposiciónItemPedido

``` text
ComposicionItemPedido
- id
- item_pedido_id FK → ItemPedido.id
- ingrediente_id FK → Ingrediente.id
- cantidad
```

Representa la composición de ingredientes comprometida para una unidad
específica del pedido en el momento en que fue enviada a cocina.

Debe existir una restricción de unicidad sobre:

``` text
(item_pedido_id, ingrediente_id)
```

para impedir duplicar un ingrediente dentro de la composición de un
ítem.

### Cuenta

``` text
Cuenta
- id
- sesion_id FK → Sesion.id
```

Una sesión tiene una sola cuenta.

No se almacena el total ni el estado.

El total se calcula a partir de los `ItemPedido` no cancelados de la
sesión.

La cuenta se considera pagada cuando todas las unidades no canceladas
han sido asignadas a pagos.

### Pago

``` text
Pago
- id
- fecha_hora
- cuenta_id FK → Cuenta.id
```

Un pago pertenece a una cuenta.

No se almacena un monto independiente: el valor se calcula a partir de
los ítems asignados.

### AsignaciónPago

``` text
AsignacionPago
- id
- pago_id FK → Pago.id
- item_pedido_id FK → ItemPedido.id
```

Relaciona un pago con una unidad concreta del consumo.

Una unidad individual de `ItemPedido` solo puede estar asignada a un
pago.

Debe existir una restricción de unicidad sobre:

``` text
item_pedido_id
```

## Reglas de negocio importantes

-   Un pedido solo se considera completo cuando todos sus ítems no
    cancelados están `LISTO`.
-   Si todos los ítems de un pedido están `CANCELADO`, el pedido se
    considera cancelado.
-   Los ítems cancelados permanecen registrados y no cuentan para
    preparación ni cuenta.
-   Un ítem solo puede cancelarse si está `EN_COLA`.
-   Los ingredientes se validan y descuentan cuando el pedido es enviado
    a cocina.
-   Si se cancela un ítem que había reservado ingredientes, las
    cantidades comprometidas deben devolverse a la disponibilidad.
-   Una modificación de un pedido que agregue o retire unidades debe
    volver a validar y ajustar las cantidades de ingredientes.
-   Un plato no disponible no puede solicitarse y debe dejar de
    ofrecerse.
-   Una mesa no puede tener dos sesiones activas simultáneamente.
-   Una sesión solo puede cerrarse cuando la cuenta está completamente
    pagada.
-   Una cuenta reúne todos los pedidos de su sesión.
-   Un mismo plato solicitado varias veces se representa mediante varios
    `ItemPedido`.
-   Una unidad de `ItemPedido` no puede dividirse entre varios pagos.
-   Un pago puede incluir unidades provenientes de diferentes pedidos de
    la misma cuenta.
-   Los pagos son registros internos; no existe procesamiento
    electrónico real.

## Consulta requerida

El sistema deberá ofrecer una consulta que represente la cola de cocina
ordenada por antigüedad y con los ítems pendientes agrupados por pedido.

La implementación concreta de esta consulta dependerá de la tecnología
seleccionada.

## Fuera de alcance

No se implementarán:

-   autenticación avanzada;
-   pagos reales o pasarelas de pago;
-   despliegue en producción;
-   integraciones externas;
-   sistema completo de inventario;
-   asignación física de cocineros;
-   entidad de comensales;
-   historial completo de cambios de recetas;
-   funcionalidades no necesarias para cumplir las reglas del enunciado.

## Principios de desarrollo

-   Priorizar el cumplimiento de las reglas de negocio indicadas en el
    enunciado.
-   Mantener el alcance limitado a las funcionalidades necesarias para
    resolver el problema planteado.
-   Evitar implementar funcionalidades que no aporten directamente al
    objetivo del sistema.
-   Las reglas de negocio importantes deben quedar reflejadas tanto en
    la documentación como en el código.
-   El código generado o propuesto mediante IA debe ser revisado y
    comprendido antes de incorporarse al proyecto.
-   Evitar almacenar información derivada cuando pueda calcularse de
    manera confiable a partir de los datos fuente.
-   Usar restricciones de integridad de la base de datos cuando sean
    apropiadas para garantizar invariantes estructurales.

## Documentación

Los principales documentos del proyecto serán:

-   `README.md`: descripción general, instalación, ejecución y
    funcionamiento.
-   `AGENTS.md`: criterios, contexto y reglas de trabajo del proyecto.
-   `ASSUMPTIONS.md`: supuestos adoptados para completar aspectos no
    especificados del problema.
-   `BITACORA-IA.md`: registro del uso de herramientas de inteligencia
    artificial durante el desarrollo.
-   `ADR/`: decisiones relevantes de arquitectura y diseño.

## Estado actual del diseño

El modelo relacional conceptual ya fue revisado y consolidado antes de
escoger la tecnología de implementación.

La tecnología de backend, frontend y base de datos todavía no se ha
seleccionado.

Antes de comenzar la implementación se deberá revisar si la tecnología
escogida permite expresar adecuadamente las restricciones identificadas
y documentar mediante ADR las decisiones tecnológicas relevantes.
