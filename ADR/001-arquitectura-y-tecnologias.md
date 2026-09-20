# ADR-001 — Arquitectura monolítica modular y tecnologías de aplicación

**Estado:** Aceptado en la sesión 3

**Contexto de trabajo:** Sesión 2 — selección tecnológica

## Contexto

El Sistema E debe permitir a meseros, cocineros y administradores gestionar sesiones de mesa, pedidos, estados independientes por ítem, disponibilidad de ingredientes y pagos parciales. Las operaciones comparten datos y reglas de negocio. La prueba técnica tiene una semana de plazo y exige un flujo completo, un repositorio reproducible y una defensa individual de las decisiones.

La estudiante prefiere React y Django REST Framework. Además, el profesor recomendó conservar el frontend y el backend en **un mismo repositorio** cuando se trabaje con un monolito.

## Decisión propuesta

Desarrollar una **aplicación web con backend monolítico modular** en Python, Django y Django REST Framework; utilizar **React con JavaScript y Vite** para la interfaz. React consumirá una API REST mediante HTTP y JSON. Django concentrará las reglas de negocio y el acceso a los datos; la interfaz mostrará la información y enviará las operaciones, pero no será la autoridad para validarlas.

Conservar `frontend/` y `backend/` como directorios separados **dentro de un único repositorio de GitHub**. Organizar la lógica de negocio del backend separadamente de las vistas de la API. Un repositorio único es una decisión de organización del código; no convierte por sí solo al sistema en monolito.

## Consecuencias

- Habrá dos directorios y procesos de desarrollo, pero un solo repositorio y un solo backend responsable del negocio.
- Deberán definirse endpoints y contratos de la API, y documentarse la ejecución local de ambas partes en `README.md`.
- El backend deberá validar estados, existencias y pagos aun cuando React ya haya efectuado validaciones visuales.
- Se asume mayor configuración inicial que con plantillas de Django; no se incorporará infraestructura de microservicios.

**Pendiente de verificar:** que ambas aplicaciones puedan instalarse y ejecutarse desde cero en otra máquina siguiendo el README.

## Actualización de la sesión 3

La estudiante confirmó la arquitectura propuesta. El repositorio contiene
`frontend/` con React y Vite, y `backend/` con Django REST Framework.
Dentro del backend, `config/` reúne la configuración y el endpoint de
salud; la aplicación `restaurant/` contiene los doce modelos del dominio,
la migración inicial y las pruebas estructurales. La configuración de
DRF incluye autenticación de sesión y autenticación básica de Django;
los permisos operativos por rol aún no están implementados.

El modelo conceptual `Usuario` se materializó como un registro del
restaurante vinculado uno a uno con `auth.User`, que conserva las
credenciales y `is_active`. En React solo se implementó la comprobación
de salud que consulta la API; los flujos de mesero y cocina siguen
pendientes. Se verificó que Vite sirve la página, que su proxy local
alcanza `/api/health/` mediante HTTP y que React compila. No se hizo una
prueba automatizada en navegador. La instalación desde cero en otra
máquina continúa pendiente de verificar.

## Estado posterior de la implementación

El apartado anterior describe el primer incremento de la sesión 3. En
los incrementos siguientes se implementaron los flujos de mesero,
cocina, cancelaciones, pagos, cierre y configuración del restaurante.
`restaurant/` separa modelos, validadores, vistas y servicios; React
conserva vistas por rol en `frontend/src/`. La API operativa aplica HTTP
Basic y comprueba `Usuario.rol` y la actividad de `auth.User` en el
backend. La cuenta ADMIN inicial se crea con un comando local y después
puede gestionar empleados MESERO y COCINERO desde React. No se añadió
autenticación avanzada ni otro servicio de negocio.

La sincronización automática y los avisos derivados de ella se
documentan en [ADR-004](004-sincronizacion-y-avisos.md). Sigue pendiente
verificar una instalación desde cero en otra máquina.
