# ADR-001 — Arquitectura monolítica modular y tecnologías de aplicación

**Estado:** Propuesto  
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
