# ADR-004 — Sincronización automática y avisos de cocina

**Estado:** Aceptado en la etapa final de la sesión 3

## Contexto y problema

La aplicación React y la API Django REST Framework se ejecutan como dos
procesos locales. Meseros, cocineros y administradores pueden modificar
pedidos, estados, existencias y catálogo desde navegadores distintos.
Una lectura única al abrir una vista dejaba datos desactualizados hasta
que el usuario pulsaba **Actualizar** o recargaba la página. Además, el
mesero necesita enterarse cuando cocina deja listo un ítem de cualquiera
de sus sesiones abiertas, aunque esté mirando otra mesa.

## Decisión

Utilizar **consultas periódicas HTTP a la API existente**. React consulta
los datos operativos aproximadamente cada 3 segundos y los datos menos
dinámicos aproximadamente cada 30 segundos, solo mientras la vista
correspondiente está activa. La lectura operativa de pedidos del mesero
abarca todas sus sesiones abiertas en una sola ruta autenticada; esa
misma respuesta actualiza la mesa seleccionada y permite detectar
transiciones observadas de `ItemPedido` hacia `LISTO`.

Los avisos reutilizan el componente visual existente. Se genera como
máximo un aviso agrupado por respuesta con novedades, sin guardar un
evento o estado de notificación en la base de datos. La primera lectura
establece una referencia y no reproduce ítems que ya estaban listos.
Los cambios y permisos siguen siendo autoridad del backend.

## Alternativas consideradas

- **Actualización manual:** ya existía, pero exigía intervención del
  usuario y no satisfacía la sincronización entre sesiones.
- **Server-Sent Events:** permitiría al servidor emitir novedades, pero
  requeriría mantener conexiones y un mecanismo para publicar eventos
  desde las operaciones de Django. No se necesitaba esa infraestructura
  para este alcance.
- **WebSockets:** permitirían comunicación bidireccional, pero las
  operaciones ya se realizan por HTTP y añadirían infraestructura y
  complejidad de autenticación y despliegue.

Estas alternativas se evaluaron para la mejora de sincronización; no se
afirma que hayan sido prototipadas ni comparadas mediante mediciones.

## Justificación y consecuencias

La solución reutiliza las rutas, autenticación y permisos de DRF, no
añade dependencias ni infraestructura y es comprensible para el alcance
local del proyecto. Las lecturas no se superponen por recurso, se
detienen al desmontar la vista o quedar oculta/sin conexión la pestaña,
se reanudan al recuperar foco/conexión y descartan respuestas antiguas.
Los formularios y datos visibles se conservan durante el refresco.

La contrapartida es una latencia aproximada de hasta el intervalo de
consulta y tráfico HTTP periódico. Los avisos dependen de observar una
transición entre dos lecturas: un ítem que aparece por primera vez ya
`LISTO` se toma como referencia y no produce aviso retroactivo. Las
notificaciones son visuales y efímeras en la pestaña abierta; no son
push del navegador ni historial durable. La frecuencia y carga no se
han medido con múltiples dispositivos. La prueba automatizada cubre el
mecanismo y los permisos. Posteriormente la estudiante comprobó
manualmente la sincronización entre sesiones, la llegada de avisos al
mesero correcto, la ausencia de avisos repetidos o ajenos y la
conservación de formularios. No se ha ejecutado una prueba automatizada
de interfaz en navegador ni una medición de carga con múltiples
dispositivos.
