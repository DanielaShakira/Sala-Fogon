# Sala Fogón

Sistema de gestión de pedidos y cocina para la prueba técnica Sistema E. El repositorio contiene Django REST Framework, React/Vite, PostgreSQL y el modelo relacional. El mesero puede abrir sesiones, consultar el catálogo, enviar pedidos, cancelar unidades en cola, registrar pagos parciales por unidad y cerrar sesiones pagadas; el cocinero puede consultar la cola y avanzar cada unidad hasta `LISTO`.

## Requisitos

- Python 3.13, Node.js 22.12 o posterior, npm y PostgreSQL local.
- Dos terminales PowerShell para ejecutar backend y frontend.

## Preparar PostgreSQL por primera vez

En esta máquina PostgreSQL 18 está instalado y el servicio escucha en el puerto 5432. En otra máquina, instala PostgreSQL y comprueba que el servicio esté activo. Los siguientes comandos **crean** un rol y dos bases nuevas; si ya existen, reutilízalos sin ejecutar las órdenes `CREATE` de nuevo.

Abre PowerShell y entra a `psql` como administrador. El parámetro `-W` solicita la contraseña en la terminal sin escribirla en el comando:

```powershell
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -U postgres -d postgres -W
```

Dentro de `psql`, comprueba primero los nombres existentes con `\du` y `\l`. Si no existen, crea el usuario, establece su contraseña de forma interactiva y crea la base:

```sql
CREATE ROLE sala_fogon_app LOGIN;
\password sala_fogon_app
CREATE DATABASE sala_fogon OWNER sala_fogon_app;
CREATE DATABASE test_sala_fogon OWNER sala_fogon_app;
\q
```

`test_sala_fogon` es exclusiva para pruebas; `--keepdb` hace que Django reutilice esa base sin requerir `CREATEDB`. No concedas `SUPERUSER`. Introduce una contraseña propia en el prompt de `\password`; no la pongas en el SQL ni en el chat.

Para comprobar la conexión del usuario, `psql` puede pedir la contraseña otra vez:

```powershell
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -h 127.0.0.1 -U sala_fogon_app -d sala_fogon -W -c 'SELECT current_database(), current_user;'
```

## Backend

Desde la raíz del repositorio:

```powershell
py -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

La configuración toma los datos de variables de entorno. También carga `backend/.env` para desarrollo local; este archivo está ignorado por Git. Puedes crearlo con un prompt que oculta la contraseña, sin ponerla en el historial ni en el chat:

```powershell
backend\.venv\Scripts\python.exe backend\configure_local.py
backend\.venv\Scripts\python.exe backend\manage.py migrate
backend\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

Si prefieres no guardar la contraseña en un archivo, establece `POSTGRES_PASSWORD` en tu sesión de PowerShell antes de ejecutar Django; las variables de entorno tienen prioridad sobre `backend/.env`. Para una instalación compartida configura también `DJANGO_SECRET_KEY` con un valor privado y desactiva `DJANGO_DEBUG`. La clave incluida en `settings.py` es solo para desarrollo local.

Abre <http://127.0.0.1:8000/api/health/>. Una conexión válida devuelve `{"api":"ok","database":"ok"}`. Si PostgreSQL no responde o faltan credenciales válidas, devuelve HTTP 503 y `database: unavailable`.

## Frontend

En otra terminal, desde la raíz:

```powershell
cd frontend
npm install
npm run dev
```

Abre la dirección mostrada por Vite, normalmente <http://localhost:5173/>. Vite reenvía las peticiones `/api` al backend en `127.0.0.1:8000`; no hay que configurar CORS para este entorno local. La interfaz ofrece vistas según el rol: ADMIN gestiona empleados, mesas y catálogo; MESERO atiende mesas y COCINERO prepara pedidos. La contraseña no se guarda en el repositorio ni en el almacenamiento del navegador; la pestaña mantiene la autorización Basic en memoria hasta salir o recargarla. Usa este flujo únicamente en el entorno local previsto, pues HTTP Basic envía credenciales en cada petición y una instalación compartida requeriría HTTPS.

Para comprobar la compilación:

```powershell
cd frontend
npm run build
```

Para comprobar la protección que descarta respuestas antiguas, el cálculo de importes y las etiquetas legibles de estados en React, ejecuta `npm test` dentro de `frontend/`. Utiliza el runner incluido en Node.js; no instala dependencias adicionales.

## Organización

- `backend/config/`: configuración Django y comprobación de salud de la API.
- `backend/restaurant/`: modelos relacionales, validadores de entrada, servicios transaccionales, vistas, administración de datos y pruebas.
- `frontend/src/`: interfaz React.
- `ADR/`, `AGENTS.md` y `ASSUMPTIONS.md`: decisiones y modelo conceptual.

## Modelo de datos

`restaurant/models.py` define las doce entidades del modelo conceptual. Django conserva el nombre y rol del restaurante en `Usuario` y gestiona las credenciales en su modelo `auth.User`, unido uno a uno con `Usuario`. La propiedad `Usuario.activo` lee `auth.User.is_active`, de modo que la actividad no se almacena dos veces. Los campos adicionales de `auth.User`, como `username` y el hash de contraseña, son soporte de autenticación y no representan nuevas entidades del negocio. La migración `restaurant.0002` retira el puntaje de carga de `Plato`; no se calcula recomendación de cocineros.

Los precios usan `DecimalField(max_digits=12, decimal_places=2)`, para conservar centavos sin errores de coma flotante. Las cantidades abstractas de ingredientes usan `DecimalField(max_digits=12, decimal_places=3)`, que permite milésimas de porción. Esto admite precios de hasta 9.999.999.999,99 y cantidades de hasta 999.999.999,999 por registro. El backend rechaza valores negativos mediante restricciones de base de datos; las recetas y composiciones comprometidas requieren cantidades mayores que cero.

La base limita a una sesión activa por mesa con una unicidad condicionada a `fecha_hora_fin IS NULL`. También garantiza una cuenta por sesión, una asignación de pago por ítem y la unicidad de ingredientes en cada receta o composición de ítem. Los estados de `Sesion`, `Pedido` y `Cuenta` no se almacenan. Las operaciones de mesero y cocina validan el rol en el backend; las transiciones, la devolución de ingredientes, los pagos y el cierre se ejecutan en transacciones.

Para ejecutar las pruebas estructurales y funcionales sobre `test_sala_fogon`, desde la raíz del repositorio:

```powershell
backend\.venv\Scripts\python.exe backend\manage.py test restaurant --keepdb --noinput
```

Antes de ejecutarlas, comprueba que `test_sala_fogon` existe, está vacía la primera vez y pertenece a `sala_fogon_app`. El comando no usa la base principal `sala_fogon` para los datos de prueba y conserva la base de pruebas al terminar.

## Administrador inicial y empleados

Para crear la primera cuenta administradora del restaurante, ejecuta una sola vez desde la raíz:

```powershell
backend\.venv\Scripts\python.exe backend\manage.py crear_administrador
```

El comando pide usuario, nombre y contraseña en la terminal; la contraseña no aparece al escribirla ni se incluye en argumentos. Crea juntos `auth.User` y `Usuario` con rol `ADMIN` en una transacción. Esta cuenta **no** es superusuaria de Django y no accede a Django Admin. Si ya existe un perfil ADMIN, utiliza esa cuenta: el comando se detiene sin crear otro. Un superusuario técnico existente puede seguir usándose para configurar mesas y catálogo en Django Admin, pero su condición de superusuario no sustituye el perfil ADMIN del restaurante.

En React, entra con la cuenta ADMIN para crear empleados con rol `MESERO` o `COCINERO` y activar o desactivar sus cuentas. No se permite crear otros ADMIN ni modificar privilegios de Django desde esta pantalla. Si un mesero tiene alguna sesión abierta, la desactivación se rechaza hasta que cierre todas sus sesiones. Los cambios de rol y la recuperación de contraseñas no forman parte de esta interfaz.

| Método y ruta | Rol | Función |
| --- | --- | --- |
| `GET /api/empleados/` | `ADMIN` | Listar meseros y cocineros con su estado activo. |
| `POST /api/empleados/` | `ADMIN` | Crear cuenta y perfil con `username`, `nombre`, `password` y `rol` (`MESERO` o `COCINERO`). |
| `PATCH /api/empleados/<id>/` | `ADMIN` | Activar o desactivar con `{"activo": true}` o `{"activo": false}`. |

## Configuración operativa del restaurante

En React, ADMIN puede crear mesas, crear ingredientes, activar o desactivar ingredientes, ajustar sus existencias y crear o editar platos con sus recetas. Las cantidades de ingredientes son porciones abstractas con tres decimales; cada cantidad de receta corresponde a **una unidad** del plato. El ajuste de existencias establece una **nueva cantidad total**: envía también la cantidad vista antes del ajuste. Si un pedido la cambió entretanto, la API devuelve HTTP 409 y el administrador debe revisar el valor actualizado antes de reintentar.

La disponibilidad se calcula desde `Plato.activo`, los ingredientes activos de la receta y las existencias requeridas. Desactivar un ingrediente no desactiva el plato ni modifica pedidos anteriores. La edición de una receta reemplaza solo su composición actual; los ítems ya enviados conservan su precio y composición históricos. El mesero puede pulsar **Actualizar catálogo** para ver los cambios sin salir de la sesión; al enviar, el backend vuelve a validar el pedido completo.

| Método y ruta | Función para `ADMIN` |
| --- | --- |
| `GET/POST /api/configuracion/mesas/` | Consultar y crear mesas con número único. |
| `GET/POST /api/configuracion/ingredientes/` | Consultar y crear ingredientes. |
| `PATCH /api/configuracion/ingredientes/<id>/estado/` | Activar o desactivar con `{"activo": true/false}`. |
| `POST /api/configuracion/ingredientes/<id>/ajustar/` | Establecer existencias con `{"cantidad_esperada": "5.000", "cantidad_nueva": "8.000"}`. |
| `GET/POST /api/configuracion/platos/` | Consultar y crear platos con su receta. |
| `PUT /api/configuracion/platos/<id>/` | Actualizar nombre, precio, estado activo y receta completa. |

La receta se envía como `"composicion": [{"ingrediente_id": 1, "cantidad_requerida": "1.250"}]`. No se permite repetir un ingrediente dentro de la misma receta. La configuración no incluye eliminación de mesas, proveedores, compras ni movimientos históricos de inventario.

## Datos iniciales y flujo del mesero

El sistema no crea mesas, platos ni ingredientes automáticamente. Para configurarlos desde cero:

1. Crea la cuenta ADMIN inicial con el comando anterior. Si ya existe, utiliza esa cuenta.
2. Entra en React como ADMIN para crear mesas, ingredientes, platos y recetas, además de las cuentas de mesero y cocinero. Si ya creaste datos o empleados manualmente, consérvalos: aparecerán en las listas correspondientes.

En React, entra con la cuenta del mesero. Una mesa sin sesión activa muestra **Abrir sesión**; una sesión propia activa puede retomarse. Añade unidades enteras de platos disponibles y confirma **Enviar a cocina**. La consulta del catálogo es informativa: el backend vuelve a comprobar los datos actuales al enviar. Si el consumo conjunto excede las existencias o alguna validación falla, no se crea el pedido ni se descuenta ingrediente alguno.

Los endpoints de este flujo son:

| Método y ruta | Función |
| --- | --- |
| `GET /api/me/` | Verificar cuenta Basic y devolver el perfil activo del restaurante. |
| `GET /api/mesas/` | Listar mesas y su sesión activa, si existe. |
| `POST /api/sesiones/` | Abrir sesión y cuenta con `{"mesa_id": 1}`. El mesero se toma de la autenticación. |
| `GET /api/platos/` | Listar platos y disponibilidad calculada desde estado, receta y existencias. |
| `POST /api/pedidos/` | Enviar `{"sesion_id": 1, "observaciones": "", "items": [{"plato_id": 1, "cantidad": 2}]}`. Cada unidad crea un `ItemPedido` en `EN_COLA`. |

Las rutas anteriores, salvo `/api/me/`, requieren HTTP Basic y el rol `MESERO`. Las cantidades de `items` deben ser números enteros JSON mayores que cero y el arreglo no puede estar vacío. Los pedidos solo pueden enviarse a una sesión activa del mesero autenticado.

## Cocina y cancelaciones

El ADMIN puede crear la cuenta de COCINERO desde React. Entra con las credenciales del cocinero. La cola muestra los pedidos pendientes de más antiguos a más recientes, agrupados por pedido y con su mesa, observaciones e ítems en `EN_COLA` o `EN_PREPARACION`. Pulsa **Iniciar** en una unidad en cola y después **Marcar listo**. La vista se actualiza tras cada operación; **Actualizar** consulta también cambios hechos desde otra pestaña. No hay actualización en tiempo real ni WebSockets.

El mesero ve todos los pedidos de la sesión seleccionada, incluidos los completados y cancelados. Se muestran como **Pedido 1**, **Pedido 2**, etc., según fecha de creación e ID dentro de esa sesión; el ID global permanece pequeño a la derecha para identificar el registro real. Puede pulsar **Actualizar** y cancelar una unidad que aún aparezca en `EN_COLA` y no esté asignada a un pago. Al cambiar de mesa se vacía la lista anterior y se ignoran las respuestas de consultas antiguas. El backend vuelve a comprobar el estado y la asignación de pago: si cocina la inició entretanto o el ítem ya fue pagado, rechaza la cancelación con HTTP 409. Una cancelación aceptada conserva el ítem en `CANCELADO` y devuelve las cantidades registradas en su composición histórica, incluso si la receta actual del plato ha cambiado. Una segunda cancelación devuelve HTTP 409 y no repite la devolución.

El estado general se **calcula al consultar**, sin columna adicional en `Pedido`: `CANCELADO` si todos los ítems están cancelados, `COMPLETO` si todos los no cancelados están listos, `EN_COLA` si todos los no cancelados siguen en cola y `EN_CURSO` para los demás avances parciales. Mesero y cocina muestran ese resumen junto con los estados individuales. Cocina conserva el ID global y solo muestra pedidos con ítems `EN_COLA` o `EN_PREPARACION`; por eso un pedido completamente listo o cancelado desaparece de su cola, pero sigue visible en la lista de su sesión para el mesero.

React muestra etiquetas legibles como **EN COLA**, **EN PREPARACIÓN** y **EN CURSO**; la API y las transiciones siguen utilizando sus códigos internos. La cola se ordena por antigüedad, sin asignación ni recomendación de cocineros.

| Método y ruta | Rol | Función |
| --- | --- | --- |
| `GET /api/sesiones/<id>/pedidos/` | `MESERO` propietario | Listar todos los pedidos e ítems de su sesión, con `numero_en_sesion` y `estado_general` calculados. |
| `GET /api/cocina/cola/` | `COCINERO` | Consultar la cola pendiente agrupada por pedido. |
| `POST /api/items/<id>/iniciar/` | `COCINERO` | Pasar de `EN_COLA` a `EN_PREPARACION`. |
| `POST /api/items/<id>/listo/` | `COCINERO` | Pasar de `EN_PREPARACION` a `LISTO`. |
| `POST /api/items/<id>/cancelar/` | `MESERO` propietario | Pasar de `EN_COLA` a `CANCELADO` y devolver ingredientes. |

Las tres operaciones de cambio de estado bloquean la fila de `ItemPedido` antes de validar el estado vigente; cancelar bloquea primero la sesión y después el ítem y los ingredientes, en ese orden. `Pedido` no guarda un estado ni existe una tabla para la cola.

## Cuenta, pagos parciales y cierre

En la vista del mesero, la sección **Cuenta de la sesión** muestra cada unidad solicitada con su precio histórico, si está pendiente o en qué pago quedó incluida. Las unidades canceladas permanecen visibles como historial y no cuentan en el consumo. La cuenta puede consultarse mientras cocina trabaja, pero el pago solo se habilita cuando **todos los ítems no cancelados de la sesión estén `LISTO`**. Entonces selecciona cualquier combinación de unidades pendientes, incluso de pedidos distintos, para ver el importe y pulsar **Registrar pago**. Puedes registrar varios pagos y repartir distintas unidades del mismo plato entre ellos. La pantalla actualiza el saldo después de cada operación. **Cerrar sesión** se habilita cuando ya no quedan unidades no canceladas sin pago; la mesa queda disponible para una nueva atención.

Los importes de la API se calculan a partir de `ItemPedido.precio_unitario`; ni `Cuenta` ni `Pago` guardan montos. React presenta una suma en centavos para que el mesero revise la selección, pero el backend vuelve a calcularla y no acepta un monto del cliente como fuente de verdad. Los ítems se asignan a un solo pago mediante `AsignacionPago`. Las escrituras de pedidos, pagos, cancelación y cierre toman primero el bloqueo de la sesión; los pagos y cancelaciones bloquean después los ítems. Así el cierre no puede validar la cuenta y dejar entrar un nuevo pedido a esa misma sesión.

| Método y ruta | Rol | Función |
| --- | --- | --- |
| `GET /api/sesiones/<id>/cuenta/` | `MESERO` propietario | Consultar pedidos, ítems facturables y cancelados, pagos y saldos derivados. También permite consultar una sesión ya cerrada. |
| `POST /api/sesiones/<id>/pagos/` | `MESERO` propietario | Registrar un pago con `{"item_ids": [1, 2]}`. Todos los ítems no cancelados de la sesión deben estar `LISTO`; los seleccionados deben ser unidades pendientes de esa cuenta abierta. |
| `POST /api/sesiones/<id>/cerrar/` | `MESERO` propietario | Cerrar cuando no queden ítems pendientes de pago. Si los hay, devuelve HTTP 409 y `item_ids_pendientes`. |

Las pruebas funcionales y de concurrencia usan exclusivamente `test_sala_fogon` con conexiones PostgreSQL independientes. Verifican la asignación única de ítems, que una cancelación en cola prevalece sobre un pago aún no habilitado, el cierre frente a un pedido nuevo y dos cierres simultáneos. La estudiante probó manualmente en el navegador el flujo de cuenta, pagos parciales y cierre. React muestra cada plato pedido en su propia fila sin exponer el ID de su ítem; esos identificadores siguen utilizándose internamente para operar cada registro individual. La compilación y las pruebas JavaScript terminaron correctamente; aún no hay una prueba automatizada de navegador. Las reglas de pago están registradas en `ASSUMPTIONS.md` y `BITACORA-IA.md`.

La prueba `restaurant` usa explícitamente `test_sala_fogon` y reutiliza esa base con `--keepdb`; no escribe datos de prueba en `sala_fogon`. Dos pruebas de carrera lanzan cancelación frente a inicio de preparación y dos cancelaciones a la vez, respectivamente. Verifican procesos PostgreSQL distintos, una sola operación aceptada y existencias finales correctas; no miden cuánto tiempo espera una solicitud en el bloqueo. Aún quedan pendientes pruebas automatizadas de navegador, de dos aperturas simultáneas y de dos envíos de pedidos simultáneos.
