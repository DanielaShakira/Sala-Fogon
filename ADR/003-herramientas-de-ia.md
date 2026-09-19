# ADR-003 — Herramientas de inteligencia artificial para el desarrollo

**Estado:** Propuesto; elección del agente por confirmar  
**Contexto de trabajo:** Sesión 3 — selección tecnológica

## Contexto

La prueba técnica exige usar IA, registrar su intervención en `BITACORA-IA.md` y defender individualmente el código y las decisiones. En las sesiones 1 y 2 **sí se utilizó ChatGPT** para analizar el enunciado, cuestionar alternativas y consolidar el modelo relacional. La metodología de `AGENTS.md` establece que la estudiante revisa propuestas y toma las decisiones finales.

Al iniciar la implementación se está considerando un agente que pueda trabajar con el código del repositorio. **Todavía no consta en la bitácora una selección definitiva ni uso efectivo de Codex.**

## Decisión propuesta

Mantener **ChatGPT** como apoyo de análisis, revisión de reglas de negocio y documentación, y **considerar Codex** como agente para proponer cambios de implementación y pruebas dentro del repositorio. Confirmar la selección de Codex después de comprobar su disponibilidad y flujo de trabajo; registrar la decisión definitiva en la bitácora antes de cambiar el estado de este ADR a «Aceptado».

La estudiante revisará los cambios, ejecutará o comprobará las pruebas y decidirá qué incorporar. Ninguna sugerencia de IA se convertirá automáticamente en requisito ni se reportará como implementada sin verificación.

## Consecuencias

- `BITACORA-IA.md` deberá distinguir solicitudes, propuestas, decisiones aceptadas o rechazadas y aspectos no verificados.
- La estudiante seguirá siendo responsable de la calidad y comprensión del código que se entregue.
- El uso de Codex solo podrá describirse como realizado cuando exista evidencia de sesiones y cambios efectivamente revisados.
- Será necesario disponer de una vía de respaldo si el agente elegido no está disponible.

**Pendiente de decidir y verificar:** confirmar el agente de implementación y documentar su primer uso real.
