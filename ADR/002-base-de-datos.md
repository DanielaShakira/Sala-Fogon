# ADR-002 — Selección del motor de base de datos

**Estado:** Aceptado en la sesión 3

**Contexto de trabajo:** Sesión 2 — selección tecnológica

## Contexto

El modelo relacional consolidado incluye mesas, sesiones, pedidos, ítems, platos, ingredientes, composiciones, cuentas y pagos. Se identificaron claves foráneas y restricciones como una sola sesión activa por mesa, una sola cuenta por sesión y una única asignación de pago por ítem. Al enviar un pedido a cocina se deben validar existencias, registrar la composición de cada unidad y descontar ingredientes conjuntamente.

Si dos meseros envían pedidos a la vez, la validación y el descuento no deben comprometer dos veces la misma existencia.

## Decisión propuesta

Utilizar **PostgreSQL** con el ORM y las migraciones de Django. Implementar las operaciones críticas de ingredientes mediante **transacciones** y una estrategia de concurrencia que bloquee los registros pertinentes antes de validar y descontar las cantidades. Aplicar restricciones de integridad, incluida una restricción de unicidad condicional para impedir más de una sesión activa por mesa.

Mantener en el backend las reglas que dependen de varios registros, como las transiciones de estados, la pertenencia de los ítems a una cuenta y la comprobación de pagos antes de cerrar una sesión. PostgreSQL no sustituye estas validaciones.

## Consecuencias

- Habrá que configurar PostgreSQL y documentar la conexión local sin publicar credenciales.
- Las migraciones deberán materializar las claves foráneas y restricciones definidas en el modelo.
- Se deberán probar reservas simultáneas, cancelaciones con devolución de ingredientes y apertura concurrente de sesiones de una mesa.
- La mayor configuración inicial deberá compensarse con una implementación que la estudiante pueda comprender y defender.
- No se implementará un inventario completo ni despliegue en producción.

**Pendiente de verificar:** conexión local, migraciones y pruebas de concurrencia; la elección del motor por sí sola no demuestra que las reglas ya se cumplan.

## Actualización de la sesión 3

La estudiante confirmó PostgreSQL. Django se conectó a la base local
`sala_fogon` y aplicó `restaurant.0001_initial`, que crea las doce
entidades. Se materializaron claves foráneas, la relación uno a uno entre
sesión y cuenta, la asignación única de un pago por ítem, la unicidad de
ingredientes por receta y por composición de ítem, y una restricción
única condicional sobre `Sesion.mesa` cuando `fecha_hora_fin IS NULL`.
También se restringieron precios y existencias no negativos,
composiciones positivas, y valores válidos de rol y estado. Los estados
derivados de sesión, pedido y cuenta no se almacenan.

Los precios se representan con `DecimalField(12, 2)` y las cantidades
abstractas de ingredientes con `DecimalField(12, 3)`. El número de
unidades solicitadas es entero porque cada unidad se guarda como un
`ItemPedido` separado. Las **13 pruebas estructurales** pasaron en la
base independiente `test_sala_fogon`; incluyeron el rechazo de una
segunda sesión activa para la misma mesa y la aceptación de una sesión
posterior tras cerrar la primera. No se comprobó todavía una carrera
real entre dos aperturas simultáneas.

La conexión local y la migración ya fueron verificadas. Siguen
pendientes las transacciones de reserva y devolución de ingredientes,
las validaciones que dependen de varias tablas, y las pruebas de
concurrencia correspondientes. La base de pruebas fue creada aparte
porque el rol de la aplicación no tiene `CREATEDB`; las credenciales
locales se mantienen fuera del repositorio.

## Estado posterior de la implementación

El apartado anterior registra la verificación estructural inicial.
Posteriormente se implementaron la reserva y devolución transaccional
de ingredientes, las transiciones de cocina, los pagos parciales y el
cierre. Las escrituras que afectan a una sesión bloquean primero su
fila; los servicios bloquean después los ítems e ingredientes que
correspondan. Se conserva la restricción única de sesión activa por
mesa y la asignación única de pago por ítem. La migración `0002` retiró
el puntaje de carga de `Plato` por decisión posterior de alcance, sin
reescribir la migración inicial.

El ajuste absoluto de existencias por ADMIN bloquea el ingrediente y
compara su cantidad vigente con la `cantidad_esperada` enviada por la
interfaz. Si cambió entretanto, rechaza el ajuste con HTTP 409 y devuelve
la cantidad actual; así evita sobrescribir un descuento concurrente de
un pedido.

Las pruebas de concurrencia posteriores usan conexiones PostgreSQL
independientes para cancelaciones, preparación, pagos y cierre, y
comprueban el estado final de los registros. No equivalen a una prueba
exhaustiva de todas las intercalaciones posibles; siguen pendientes
pruebas específicas de dos aperturas de mesa y dos envíos de pedido
simultáneos. Los importes y estados derivados no se almacenan como
columnas adicionales.
