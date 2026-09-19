# ADR-002 — Selección del motor de base de datos

**Estado:** Propuesto  
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
